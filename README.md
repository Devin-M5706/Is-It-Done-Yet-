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
| `pipeline.py` | Sense pipeline + Random Forest. Smoothing, overlapping windows, features (variance, skew/kurtosis, FFT band powers, inter-axis correlation), persistence + hysteresis trigger. |
| `server.py` | Laptop brain: aiohttp HTTPS + WebSocket, self-signed cert, live console readout. |
| `static/index.html` | Phone page: streams accelerometer, renders the breathing pacer (visual + vibration + audio). |

## Honest caveats (say these to the mentor)

- **Classifier is trained on synthetic calm/agitated motion** — a placeholder. Accuracy is borrowed, not earned on real panic data yet. The pipeline is real; the data isn't.
- **iPhone has no web Vibration API** — on iOS you get the visual + audio pacer but no buzz. Android Chrome gets the full haptic. (This is a browser limit, not a design flaw — a real wristband/board or an Android phone restores the haptic.)
- **Wrist motion is a proxy** — some panic presents as freezing/stillness, which motion alone misses.
- **DeviceMotion needs HTTPS + a tap** (handled by the Start button + self-signed cert).

## Tuning knobs

- Breathing cadence: `INHALE` / `EXHALE` in `server.py` (default 4s in / 6s out ≈ 6 breaths/min).
- Trigger sensitivity: `HIGH`, `LOW`, `K_TRIGGER`, `K_RELEASE` in `pipeline.py`.
- Real data later: replace `_make_synthetic()` in `pipeline.py` with recorded windows; everything downstream is unchanged.
