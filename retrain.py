"""
Retrain the agitation classifier on captured recordings.

Recordings live in data/raw/*.jsonl — one line per accel frame:
    {"t": <epoch ms>, "label": "calm"|"agitated"|"none", "s": [[ax,ay,az], ...]}

Frames are written by server.py while a hold-to-record button is held (or for
every frame with --capture). Windows whose majority label is "none" are
dropped. Evaluation uses GroupKFold over recordings so a session can't leak
into its own test fold.

Usage:
    python retrain.py                      # train on data/raw/*.jsonl
    python retrain.py --fake-recordings 3  # synthesize 3 recordings, then train

Outputs: data/model.joblib (auto-loaded by server.py) and
data/RETRAIN_REPORT.md (metrics + threshold recommendations).
"""

import argparse
import datetime
import json
import pathlib
import sys

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import GroupKFold

import pipeline
from pipeline import (
    DATA_DIR,
    FEATURE_NAMES,
    FS,
    HIGH,
    K_RELEASE,
    K_TRIGGER,
    LOW,
    MODEL_PATH,
    RF_PARAMS,
    extract_features,
    iter_windows,
    synthetic_window,
)

RAW_DIR = DATA_DIR / "raw"
REPORT_PATH = DATA_DIR / "RETRAIN_REPORT.md"
LABELS = {"calm": 0, "agitated": 1}
CHUNK = 10  # samples per jsonl frame, mimics the phone's ~80ms flush


def make_fake_recording(path, seed):
    """Write a fake recording: ~25 alternating labeled segments built from
    synthetic_window(), plus one short 'none' segment to exercise the drop."""
    rng = np.random.default_rng(seed)
    t_ms = 1_700_000_000_000
    none_at = rng.integers(5, 20)  # insert the "none" segment mid-stream
    with open(path, "w") as f:
        for seg in range(25):
            if seg == none_at:
                label = "none"
                win = synthetic_window(rng, 0) * 0.5
            else:
                label = "calm" if seg % 2 == 0 else "agitated"
                win = synthetic_window(rng, LABELS[label])
            flat = win.tolist()
            for i in range(0, len(flat), CHUNK):
                chunk = flat[i:i + CHUNK]
                f.write(json.dumps(
                    {"t": t_ms, "label": label, "s": chunk}) + "\n")
                t_ms += int(len(chunk) / FS * 1000)


def load_recording(path):
    """-> (samples (N,3), per-sample labels list, per-label sample counts)."""
    samples, labels = [], []
    counts = {"calm": 0, "agitated": 0, "none": 0}
    bad = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                lab = rec["label"] if rec["label"] in counts else "none"
                for s in rec["s"]:
                    ax, ay, az = s
                    samples.append((float(ax), float(ay), float(az)))
                    labels.append(lab)
                    counts[lab] += 1
            except (ValueError, KeyError, TypeError):
                bad += 1
    if bad:
        print(f"  warning: skipped {bad} malformed line(s) in {path.name}")
    return np.array(samples), labels, counts


def metrics(y_true, y_pred):
    return {
        "acc": accuracy_score(y_true, y_pred),
        "prec": precision_score(y_true, y_pred, zero_division=0),
        "rec": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "cm": confusion_matrix(y_true, y_pred, labels=[0, 1]),
    }


def longest_run(mask):
    best = run = 0
    for v in mask:
        run = run + 1 if v else 0
        best = max(best, run)
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fake-recordings", type=int, default=0, metavar="N",
                    help="synthesize N fake recordings into data/raw first")
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for i in range(args.fake_recordings):
        p = RAW_DIR / f"fake_{i}.jsonl"
        make_fake_recording(p, 100 + i)
        print(f"[fake] wrote {p}")

    files = sorted(RAW_DIR.glob("*.jsonl"))
    if len(files) < 2:
        sys.exit(f"need >=2 recordings in {RAW_DIR}, found {len(files)} — "
                 "hold the CALM/AGITATED buttons to record, or use --fake-recordings")

    # ---- load + window each recording -------------------------------------
    X, y, groups = [], [], []
    rec_rows = []          # per-recording report rows
    rec_windows = {}       # group -> list of window indices (for run analysis)
    for gi, path in enumerate(files):
        samples, labels, counts = load_recording(path)
        n_win = 0
        rec_windows[gi] = []
        for win, lab in iter_windows(samples, labels):
            if lab not in LABELS:
                continue  # majority 'none' — drop
            rec_windows[gi].append(len(X))
            X.append(extract_features(win))
            y.append(LABELS[lab])
            groups.append(gi)
            n_win += 1
        secs = {k: v / FS for k, v in counts.items()}
        rec_rows.append((path.name, secs["calm"], secs["agitated"], secs["none"], n_win))
        print(f"[load] {path.name}: {secs['calm']:.1f}s calm, "
              f"{secs['agitated']:.1f}s agitated, {secs['none']:.1f}s none, "
              f"{n_win} windows")

    X, y, groups = np.array(X), np.array(y), np.array(groups)
    n_groups = len(files)
    if len(set(y)) < 2:
        sys.exit("need both 'calm' and 'agitated' windows — a class is missing")
    if n_groups < 2:
        sys.exit(f"need >=2 recordings, found {n_groups}")

    # ---- group-wise cross-validation --------------------------------------
    cv = GroupKFold(n_splits=min(5, n_groups))
    oof_prob = np.zeros(len(y))
    for tr, te in cv.split(X, y, groups):
        m = RandomForestClassifier(**RF_PARAMS)
        m.fit(X[tr], y[tr])
        oof_prob[te] = m.predict_proba(X[te])[:, 1]
    oof_pred = (oof_prob >= 0.5).astype(int)
    cv_m = metrics(y, oof_pred)
    print(f"\n[cv] acc {cv_m['acc']:.3f}  prec {cv_m['prec']:.3f}  "
          f"rec {cv_m['rec']:.3f}  f1 {cv_m['f1']:.3f}")
    print(f"[cv] confusion (rows=true calm/agit):\n{cv_m['cm']}")

    # ---- synthetic baseline on the same real windows -----------------------
    syn = pipeline.Classifier(model_path=None)
    syn_prob = syn.model.predict_proba(X)[:, 1]
    syn_pred = (syn_prob >= 0.5).astype(int)
    syn_m = metrics(y, syn_pred)
    print(f"[synthetic-baseline] acc {syn_m['acc']:.3f}  prec {syn_m['prec']:.3f}  "
          f"rec {syn_m['rec']:.3f}  f1 {syn_m['f1']:.3f}")

    # ---- final model on all real windows -----------------------------------
    final = RandomForestClassifier(**RF_PARAMS)
    final.fit(X, y)
    train_acc = final.score(X, y)
    joblib.dump({
        "model": final,
        "train_acc": train_acc,
        "n_windows": len(X),
        "n_recordings": n_groups,
        "feature_names": FEATURE_NAMES,
        "trained_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }, MODEL_PATH)
    print(f"[model] wrote {MODEL_PATH} (train acc {train_acc:.3f}, "
          f"{len(X)} windows, {n_groups} recordings)")

    # ---- threshold / persistence analysis on out-of-fold probs --------------
    calm_p = oof_prob[y == 0]
    agit_p = oof_prob[y == 1]
    calm_pct = np.percentile(calm_p, [50, 90, 95, 99])
    agit_pct = np.percentile(agit_p, [1, 5, 10, 50])

    fp_run = max((longest_run((oof_prob[idx] >= HIGH) & (y[idx] == 0))
                  for idx in rec_windows.values() if len(idx)), default=0)
    fc_run = max((longest_run((oof_prob[idx] <= LOW) & (y[idx] == 1))
                  for idx in rec_windows.values() if len(idx)), default=0)

    recs = []
    if len(calm_p) and calm_pct[2] > HIGH:
        recs.append(f"- HIGH: calm p95 is {calm_pct[2]:.2f} > {HIGH} — "
                    f"consider raising HIGH to ~{round(calm_pct[2] + 0.05, 2):.2f}")
    elif len(agit_p) and agit_pct[1] < HIGH:
        recs.append(f"- HIGH: agitated p5 is {agit_pct[1]:.2f} < {HIGH} — "
                    "HIGH may be too high for the weakest agitated episodes")
    else:
        recs.append(f"- HIGH: keep {HIGH}")
    if len(calm_p) and calm_pct[0] > LOW:
        recs.append(f"- LOW: calm p50 is {calm_pct[0]:.2f} > {LOW} — "
                    f"consider raising LOW to ~{round(calm_pct[0] + 0.05, 2):.2f}")
    else:
        recs.append(f"- LOW: keep {LOW}")
    if fp_run >= K_TRIGGER:
        recs.append(f"- K_TRIGGER: longest calm false-positive run is {fp_run} "
                    f"windows — consider K_TRIGGER >= {fp_run + 1}")
    else:
        recs.append(f"- K_TRIGGER: keep {K_TRIGGER} (longest false-positive run {fp_run})")
    if fc_run >= K_RELEASE:
        recs.append(f"- K_RELEASE: longest agitated false-calm run is {fc_run} "
                    f"windows — consider K_RELEASE >= {fc_run + 1}")
    else:
        recs.append(f"- K_RELEASE: keep {K_RELEASE} (longest false-calm run {fc_run})")

    # ---- report ------------------------------------------------------------
    imp = sorted(zip(FEATURE_NAMES, final.feature_importances_),
                 key=lambda kv: -kv[1])[:10]
    cm = cv_m["cm"]
    lines = [
        "# Retrain report",
        "",
        f"_generated {datetime.datetime.now().isoformat(timespec='seconds')}_",
        "",
        "## Recordings",
        "",
        "| file | calm s | agitated s | none s | windows |",
        "|---|---|---|---|---|",
        *[f"| {n} | {c:.1f} | {a:.1f} | {o:.1f} | {w} |"
          for n, c, a, o, w in rec_rows],
        "",
        f"Total: **{len(X)} windows** from **{n_groups} recordings** "
        f"({int((y == 0).sum())} calm / {int((y == 1).sum())} agitated).",
        "",
        "## Cross-validation (GroupKFold by recording, out-of-fold)",
        "",
        "| metric | value |",
        "|---|---|",
        f"| accuracy | {cv_m['acc']:.3f} |",
        f"| precision (agitated) | {cv_m['prec']:.3f} |",
        f"| recall (agitated) | {cv_m['rec']:.3f} |",
        f"| f1 (agitated) | {cv_m['f1']:.3f} |",
        "",
        "Confusion matrix (rows = true, cols = predicted; calm, agitated):",
        "",
        "```",
        f"{cm[0]}",
        f"{cm[1]}",
        "```",
        "",
        "## Synthetic vs real (same windows, threshold 0.5)",
        "",
        "| model | acc | prec | rec | f1 |",
        "|---|---|---|---|---|",
        f"| retrained (OOF) | {cv_m['acc']:.3f} | {cv_m['prec']:.3f} | {cv_m['rec']:.3f} | {cv_m['f1']:.3f} |",
        f"| synthetic baseline | {syn_m['acc']:.3f} | {syn_m['prec']:.3f} | {syn_m['rec']:.3f} | {syn_m['f1']:.3f} |",
        "",
        "## Top-10 feature importances (final model)",
        "",
        "| feature | importance |",
        "|---|---|",
        *[f"| {n} | {v:.3f} |" for n, v in imp],
        "",
        "## Threshold analysis (out-of-fold probabilities)",
        "",
        f"- calm windows: p50 {calm_pct[0]:.2f}, p90 {calm_pct[1]:.2f}, "
        f"p95 {calm_pct[2]:.2f}, p99 {calm_pct[3]:.2f}",
        f"- agitated windows: p1 {agit_pct[0]:.2f}, p5 {agit_pct[1]:.2f}, "
        f"p10 {agit_pct[2]:.2f}, p50 {agit_pct[3]:.2f}",
        "",
        f"Current constants: HIGH={HIGH}, LOW={LOW}, "
        f"K_TRIGGER={K_TRIGGER}, K_RELEASE={K_RELEASE}",
        "",
        "### Recommendations",
        "",
        *recs,
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines))
    print(f"[report] wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
