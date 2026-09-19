# Architecture

Passive panic co-regulation: a wrist motion sensor streams acceleration to a
laptop "brain" that classifies agitation and, on sustained agitation, drives
paced-breathing actuators. One frozen message contract, two sensor sources
(phone today, ESP32 wristband when hardware lands). This file describes what
exists in the repo now and the hackathon target; status is marked per component.

## 1. Component diagram

```
 SENSORS                      BRAIN (laptop)                         ACTUATORS
 ───────                      ──────────────                         ─────────
 phone browser                                                       phone pacer
 static/index.html ──wss /ws──► server.py ─┐                     ┌──► (visual+vibrate+audio)
 {"type":"accel"}   ◄──────────────────────┤ {"type":"breathe"}  │    static/index.html
                                           │                     │
 ESP32 wristband                           ├─► StreamProcessor ──┤   ESP32 wristband haptic
 firmware/wristband ──BLE notify──► ble_bridge.py   (pipeline.py) │    LEDC PWM on PIN_HAPTIC
 ACCEL char         ◄──BLE write────────────┤       │             │    ◄── BREATHE char
                                           │   Classifier (RF)   │
                                           │       │             │   ESP32 plush
                                           │  persistence +      └ ─ ► firmware/plush
                                           │  hysteresis trigger  (not wired: nothing
                                           │                       writes STATE yet)
                                           └─► {"type":"state"} ──► dashboard
                                                                   (phone page bar today;
                                                                    GLUE dashboard = target)
```

Solid arrows exist in code. The dashed arrow to the plush is the target: the
plush firmware exposes a STATE characteristic but no brain-side code writes it.

## 2. Message contract (frozen after sprint hour 2)

Any change here must change the sender, the receiver, this table and
`.agents/skills/esp32-firmware/SKILL.md` in the same PR.

### WebSocket JSON (phone ↔ `server.py`, path `/ws`, HTTPS port 8443)

| Direction | Message | Fields | Source |
|---|---|---|---|
| phone → brain | `accel` | `{"type":"accel","s":[[ax,ay,az], ...]}` — floats from `DeviceMotionEvent.accelerationIncludingGravity` (m/s²), batched every 80 ms | `static/index.html`, `server.py` |
| brain → phone | `state` | `{"type":"state","prob":0.0-1.0,"triggered":bool}` — one per hop | `server.py` |
| brain → phone | `breathe` | `{"type":"breathe","action":"start","inhale":4.0,"exhale":6.0}` or `{"type":"breathe","action":"stop"}` | `server.py` (`INHALE`, `EXHALE`) |
| phone → brain | `capture` | `{"type":"capture","action":"start","label":"calm"\|"agitated"}` / `{"type":"capture","action":"stop"}`; brain echoes `{"type":"capture","state":"recording"\|"saved",...}` | `server.py` (main); PR #2 replaces this with `label` |
| phone → brain | `label` | `{"type":"label","value":"calm"\|"agitated"\|null}` — tags subsequent `accel` samples for jsonl capture | `server.py` in PR #2 (`retrain.py` flow) |

### BLE GATT (ESP32 ↔ `ble_bridge.py`)

UUID suffix for all: `-1e3c-4f5a-9b2d-8c7e6f5a4b3c`.

| Device / advertised name | Service | Characteristic | Property | Payload (byte layout) | Source |
|---|---|---|---|---|---|
| wristband `panic-wrist` | `9a0b0001-…` | ACCEL `9a0b0002-…` | NOTIFY (+BLE2902 CCCD) | `SAMPLES_PER_PACKET`=4 samples × `int16 ax, ay, az` little-endian, **milli-g** → 24 bytes/notify. Bridge decodes `struct.unpack("<" + "h"*3n)` and divides by 1000 → g | `wristband/main.cpp`, `ble_bridge.py` |
| wristband `panic-wrist` | `9a0b0001-…` | BREATHE `9a0b0003-…` | WRITE (no response) | 3 bytes `[action(0=stop,1=start), inhale_s, exhale_s]`; bridge packs `struct.pack("BBB", ...)` with `INHALE, EXHALE = 4, 6` | `ble_bridge.py`, `wristband/main.cpp` |
| plush `panic-plush` | `9a0b1001-…` | STATE `9a0b1002-…` | WRITE | 4 bytes `[mode(0=calm,1=rising,2=breathing,3=settling), heartbeat_bpm, breathe_phase(0=in,1=out), secs]`; firmware currently reads only bytes 0–1 | `plush/main.cpp` (no writer exists) |

Unit note: the phone path feeds m/s² and the BLE path feeds g into the same
`StreamProcessor`; features are scale-sensitive, so a model trained on phone
data is not directly transferable to wristband data (calibrate or rescale one).

## 3. Where each lane's code lives

| Lane | Owns | Files |
|---|---|---|
| SENSE | wristband firmware, BLE bridge | `firmware/wristband/main.cpp`, `ble_bridge.py`, `firmware/platformio.ini`, `firmware/README.md` |
| BRAIN | features, classifier, trigger, capture/retrain | `pipeline.py` (`extract_features`, `Classifier`, `StreamProcessor`), `train.py` → `retrain.py` (PR #2), `data/` |
| ACT | pacer, wristband haptic, plush, (target) Claude/ElevenLabs/988 | `static/index.html` (pacer), `firmware/wristband/main.cpp` (`updateHaptic`), `firmware/plush/main.cpp`, `PLUSH.md` |
| GLUE | server, transport, dashboard, demo | `server.py`, `static/index.html` (agitation bar), `.github/workflows/firmware.yml`, `SPRINT_PLAN.md`, `DEMO_READINESS.md` |

## 4. Data flow for one trigger event

Timing knobs (from `pipeline.py` unless noted):

| Knob | Value | Meaning |
|---|---|---|
| `FS` | 50.0 Hz | nominal sample rate for FFT bins (phone ~60 Hz, ESP32 `SAMPLE_HZ` = 50) |
| `WINDOW_N` | 128 samples | ≈2.5 s window at 50 Hz |
| `HOP_N` | 32 samples | ≈0.64 s between classifications |
| `SMOOTH_K` | 5 | moving-average kernel before features |
| `HIGH` / `LOW` | 0.60 / 0.35 | hysteresis thresholds on probability |
| `K_TRIGGER` / `K_RELEASE` | 4 / 4 | consecutive windows ≥HIGH to fire / ≤LOW to release (≈2.5 s each) |
| `INHALE` / `EXHALE` | 4 s / 6 s | `server.py` and `ble_bridge.py`; ≈6 breaths/min |
| `SAMPLES_PER_PACKET` | 4 | `wristband/main.cpp`; one notify per 80 ms |

Step by step:

1. Sensor samples at ~50 Hz. Phone: `onMotion` pushes `[x,y,z]`, flushed as one
   `accel` message every 80 ms. ESP32: `loop()` reads MPU6050 registers 0x3B–0x40
   every `SAMPLE_US`, converts raw LSB → milli-g (`LSB_PER_G` = 16384), notifies
   every 4 samples.
2. Transport delivers to the brain: `server.py ws_handler` or `ble_bridge.py
   on_accel`. Each sample goes to `StreamProcessor.add(ax, ay, az)`.
3. `StreamProcessor` buffers into a `deque(maxlen=WINDOW_N)`; returns `None`
   until the buffer is full and `HOP_N` new samples arrived (first result after
   128 samples ≈ 2.5 s, then every 32 samples).
4. `Classifier.prob(window)` → `extract_features` (smoothing, detrended magnitude
   std/var, per-axis std, skew, kurtosis, mean jerk, FFT band powers 0.5–3 /
   3–8 / 8–20 Hz, dominant frequency, inter-axis correlations) → Random Forest
   `predict_proba` → `prob`.
5. Persistence + hysteresis: `hi_run` increments while `prob >= HIGH`, resets
   otherwise. When `hi_run >= K_TRIGGER` and not already triggered →
   `triggered=True, trigger_changed=True`. Worst-case latency from sustained
   agitation to fire ≈ `K_TRIGGER × HOP_N / FS` ≈ 2.6 s plus window fill.
6. Fan-out on `trigger_changed`: phone gets `breathe start` (pacer runs
   `INHALE`/`EXHALE`, vibrates on Android, tone swells); wristband gets
   `[1, 4, 6]` on BREATHE → `updateHaptic` buzzes PWM 120/255 during exhale,
   off during inhale, non-blocking. Every hop also emits `state` for the bar.
7. Release: `lo_run` counts windows with `prob <= LOW`; at `K_RELEASE` →
   `triggered=False`, `breathe stop` / `[0, 4, 6]`, haptic off.

## 5. Status: real vs. untested

| Component | Status |
|---|---|
| Phone → `server.py` → pipeline → pacer loop | **Verified** on a real phone (Android haptic; iOS visual+audio only) |
| `pipeline.py` classifier | Runs; ships as a **synthetic placeholder** model until real data is captured |
| Data capture + retraining | main: CSV + `train.py`; PR #2: jsonl + `retrain.py` (in review) |
| `firmware/wristband/main.cpp` | **Compiles** (`pio run -e wristband`); never run on hardware |
| `firmware/plush/main.cpp` | **Compiles** (`pio run -e plush`); never run on hardware; no brain-side writer for STATE |
| `ble_bridge.py` | Written to the contract; **untested** against hardware (needs `bleak` + a board) |
| Plush ↔ brain wiring, Claude/ElevenLabs voice, 988 safety layer, GLUE dashboard | **Not started** (SPRINT_PLAN targets) |
| BLE notify size | 24-byte payload exceeds the 20-byte default ATT MTU payload; see `.agents/skills/esp32-firmware/SKILL.md` |
