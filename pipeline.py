"""
Sense pipeline: raw accel stream -> smoothing -> sliding windows -> features
-> Random Forest -> agitation probability -> persistence-based trigger.

This mirrors the wristband detection design, but the phone is the sensor.
The classifier is trained on SYNTHETIC calm/agitated motion (placeholder) --
accuracy is borrowed, not yet earned on real panic data. Swap in real,
per-person data later; the rest of the pipeline stays the same.
"""

from collections import deque

import numpy as np
from scipy import stats
from sklearn.ensemble import RandomForestClassifier

# ---- constants (kept identical for training AND inference so the feature
#      space is consistent even though FS is a nominal assumption) ----------
FS = 50.0            # nominal sample rate (Hz) used for frequency features
WINDOW_N = 128       # samples per window (~2.1-2.5s on a real phone)
HOP_N = 32           # new samples between windows (overlap -> ~0.5s hop)
SMOOTH_K = 5         # moving-average kernel (kills sensor hash)

# trigger logic (persistence + hysteresis: sustained agitation, not one twitch)
HIGH = 0.60          # prob above this counts as an "agitated" window
LOW = 0.35           # prob below this counts as a "calm" window
K_TRIGGER = 4        # consecutive agitated windows required to fire (~2s)
K_RELEASE = 4        # consecutive calm windows required to stand down


def _moving_average(x, k):
    if k <= 1 or x.shape[0] < k:
        return x
    kernel = np.ones(k) / k
    return np.apply_along_axis(lambda c: np.convolve(c, kernel, mode="same"), 0, x)


def extract_features(win):
    """win: np.ndarray shape (N, 3) of raw acceleration. Returns 1-D feature vector."""
    win = _moving_average(np.asarray(win, dtype=float), SMOOTH_K)

    # magnitude, detrended to strip the gravity/DC component
    mag = np.linalg.norm(win, axis=1)
    mag = mag - mag.mean()

    feats = []

    # --- amplitude of movement (agitation = bigger swings) ---
    feats.append(mag.std())
    feats.append(mag.var())
    feats += [win[:, i].std() for i in range(3)]

    # --- shape: jerky/spiky (anxious) vs smooth (calm) ---
    feats.append(stats.skew(mag) if mag.std() > 1e-9 else 0.0)
    feats.append(stats.kurtosis(mag) if mag.std() > 1e-9 else 0.0)
    feats.append(np.abs(np.diff(mag)).mean())  # mean jerk

    # --- frequency content: tremor/fidget tempo (FFT/PSD band powers) ---
    psd = np.abs(np.fft.rfft(mag)) ** 2
    freqs = np.fft.rfftfreq(len(mag), d=1.0 / FS)
    total = psd.sum() + 1e-12
    for lo, hi in [(0.5, 3.0), (3.0, 8.0), (8.0, 20.0)]:
        band = psd[(freqs >= lo) & (freqs < hi)].sum()
        feats.append(band / total)
    feats.append(freqs[1 + int(np.argmax(psd[1:]))])  # dominant freq (skip DC)

    # --- inter-axis coordination (purposeful vs multi-axis agitated) ---
    with np.errstate(invalid="ignore"):
        c = np.corrcoef(win.T)
    feats += [
        0.0 if np.isnan(c[0, 1]) else c[0, 1],
        0.0 if np.isnan(c[0, 2]) else c[0, 2],
        0.0 if np.isnan(c[1, 2]) else c[1, 2],
    ]

    return np.array(feats, dtype=float)


def _make_synthetic(n_per_class=400, seed=7):
    """Generate calm vs agitated windows. Placeholder data until real panic
    signals exist -- see module docstring."""
    rng = np.random.default_rng(seed)
    X, y = [], []
    t = np.arange(WINDOW_N) / FS

    for _ in range(n_per_class):
        # CALM: low-amplitude, low-frequency, smooth, coherent sway
        amp = rng.uniform(0.02, 0.08)
        f = rng.uniform(0.1, 0.5)
        phase = rng.uniform(0, 2 * np.pi)
        base = amp * np.sin(2 * np.pi * f * t + phase)
        win = np.stack([base, base * 0.8, base * 0.6], axis=1)
        win += rng.normal(0, 0.01, win.shape)
        win += rng.uniform(-1, 1, 3)  # random gravity offset
        X.append(extract_features(win)); y.append(0)

        # AGITATED: high-amplitude, 3-10 Hz energy, spiky, incoherent axes
        amp = rng.uniform(0.2, 0.8)
        f = rng.uniform(3.0, 10.0)
        win = np.stack([
            amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi))
            for _ in range(3)
        ], axis=1)
        win += rng.normal(0, 0.08, win.shape)
        spikes = rng.integers(3, 9)
        for _ in range(spikes):  # impulses -> high kurtosis
            idx = rng.integers(0, WINDOW_N)
            win[idx] += rng.uniform(-1.5, 1.5, 3)
        win += rng.uniform(-1, 1, 3)
        X.append(extract_features(win)); y.append(1)

    return np.array(X), np.array(y)


class Classifier:
    """Random Forest -> agitation probability. Lightweight, interpretable,
    resistant to overfitting on small data, gives a graded probability."""

    def __init__(self):
        X, y = _make_synthetic()
        self.model = RandomForestClassifier(
            n_estimators=200, max_depth=8, random_state=7, n_jobs=-1
        )
        self.model.fit(X, y)
        self.train_acc = self.model.score(X, y)

    def prob(self, win):
        f = extract_features(win).reshape(1, -1)
        return float(self.model.predict_proba(f)[0, 1])


class StreamProcessor:
    """Buffers a live sample stream, emits an event once per hop with the
    agitation probability and a persistence/hysteresis-gated trigger flag."""

    def __init__(self, clf):
        self.clf = clf
        self.buf = deque(maxlen=WINDOW_N)
        self.since_last = 0
        self.hi_run = 0
        self.lo_run = 0
        self.triggered = False

    def add(self, ax, ay, az):
        self.buf.append((ax, ay, az))
        self.since_last += 1
        if len(self.buf) < WINDOW_N or self.since_last < HOP_N:
            return None
        self.since_last = 0

        prob = self.clf.prob(np.array(self.buf))

        # persistence + hysteresis
        self.hi_run = self.hi_run + 1 if prob >= HIGH else 0
        self.lo_run = self.lo_run + 1 if prob <= LOW else 0
        changed = False
        if not self.triggered and self.hi_run >= K_TRIGGER:
            self.triggered, changed, self.lo_run = True, True, 0
        elif self.triggered and self.lo_run >= K_RELEASE:
            self.triggered, changed, self.hi_run = False, True, 0

        return {"prob": prob, "triggered": self.triggered, "trigger_changed": changed}
