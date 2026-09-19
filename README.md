# Panic co-regulation — Tier 0 (phone as the wrist sensor)

The full detection→intervention loop with **zero hardware**. The phone is the
IMU + the wireless link + the haptic; your laptop is the "brain."

```
phone accelerometer ──wss──► laptop: smooth → window → features → Random Forest
        ▲                                              │  agitation probability
        │                                    persistence + hysteresis trigger
   vibrate + visual + audio  ◄──breathe cmd──────────────┘
```

## Run it

```bash
cd panic-sensor-tier0
python -m venv .venv && .venv\Scripts\activate      # Windows (PowerShell/Git Bash)
pip install -r requirements.txt
python server.py
```

The server prints a URL like `https://192.168.x.x:8443`.

**On the phone (same Wi-Fi as the laptop):**
1. Open that URL in the browser.
2. Accept the certificate warning ("Advanced → proceed"). It's self-signed — that's expected, and DeviceMotion needs the secure context.
3. Tap **Start**, then **Allow** motion access.
4. Strap/hold the phone to your wrist. Watch the agitation bar. **Shake/fidget it hard for ~2s** → the pacer fires: the circle breathes, the phone vibrates, a soft tone swells. Hold still → it stands down.
5. **Test breathing** runs the pacer on demand (for demos, no shaking needed).

## What each piece does

| File | Role |
|------|------|
| `pipeline.py` | Sense pipeline + Random Forest. Smoothing, overlapping windows, features (variance, skew/kurtosis, FFT band powers, inter-axis correlation), persistence + hysteresis trigger. Loads a real model if one exists, else a synthetic placeholder. |
| `server.py` | Laptop brain: aiohttp HTTPS + WebSocket, self-signed cert, **data-capture recording**, live console readout. |
| `static/index.html` | Phone page: streams accelerometer, renders the breathing pacer (visual + vibration + audio), **record buttons**. |
| `train.py` | Trains on real captured data with honest, leak-free (GroupKFold-by-session) metrics. |
| `ble_bridge.py` | Bridges an ESP32 wristband (BLE) into the same pipeline. **Untested — no hardware yet.** |
| `firmware/` | ESP32 sketches for the wristband + plush. **Boilerplate, untested.** See `firmware/README.md`. |

## Capture real data, then train on it

The shipped model is a **synthetic placeholder** (`pipeline.py` says so on startup).
To replace it with a model trained on real wrists:

1. `python server.py`, open the phone page, tap **Start**.
2. Sit still and tap **● Rec calm** → do calm/normal wrist motion for ~30–60s → tap **■ Stop**.
3. Tap **● Rec agitated** → fidget/shake vigorously for ~30–60s → **■ Stop**.
4. Repeat with different people / a few sessions each (more sessions = a real held-out score).
5. `python train.py` — prints honest cross-validated metrics and writes `data/model.joblib`.
6. Restart `server.py`; it loads the real model automatically (startup banner confirms).

Each recording is one CSV in `data/` and one "session." `train.py` holds out whole
sessions, so its accuracy isn't inflated by correlated windows — and it prints **no**
score at all if you have fewer than 2 recordings per class.

## Hardware path (when the ESP32s arrive)

The phone loop and the wristband speak the **same contract**, so hardware is a
drop-in swap, not a rewrite:

1. Flash `firmware/wristband/wristband.ino` (see `firmware/README.md`).
2. `pip install bleak`, then `python ble_bridge.py` — it feeds the ESP32's BLE
   accel stream into the *same* `StreamProcessor` and writes breathe commands back.

Everything downstream (features, classifier, trigger logic) is unchanged.

## Honest caveats (say these to the mentor)

- **Classifier ships as a synthetic placeholder** — no real accuracy is claimed until you capture data and run `train.py`, which reports honest, held-out numbers from *your* data. The pipeline is real; the shipped data isn't.
- **iPhone has no web Vibration API** — on iOS you get the visual + audio pacer but no buzz. Android Chrome gets the full haptic. (This is a browser limit, not a design flaw — a real wristband/board or an Android phone restores the haptic.)
- **Wrist motion is a proxy** — some panic presents as freezing/stillness, which motion alone misses.
- **DeviceMotion needs HTTPS + a tap** (handled by the Start button + self-signed cert).

## Tuning knobs

- Breathing cadence: `INHALE` / `EXHALE` in `server.py` (default 4s in / 6s out ≈ 6 breaths/min).
- Trigger sensitivity: `HIGH`, `LOW`, `K_TRIGGER`, `K_RELEASE` in `pipeline.py`.
- Real data: capture with the phone's record buttons, then `python train.py` (see above).
