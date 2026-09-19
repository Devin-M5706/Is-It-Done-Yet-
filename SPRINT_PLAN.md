# 24-Hour Sprint Plan — Passive Panic Co-Regulation System

**Team:** 4 people, prior hackathon experience · **Hardware:** full access, but not on hand at start · **Constraint that shapes everything:** hardware is *not* on the critical path.

---

## 0. The one strategic bet: one contract, two sensor sources

The single decision that de-risks this whole sprint:

> **Everything talks through a fixed message contract. The phone implements it today; the ESP32 implements it when parts arrive. Nothing else in the system changes when you switch.**

This means:
- You demo a **complete working loop within the first 2 hours** (phone as sensor — already built and verified).
- Hardware becomes an **upgrade**, not a dependency. If parts arrive at hour 3 or hour 18 — or never — you still have a full demo.
- Four people build in parallel against the contract without stepping on each other.

The contract (already implemented in the Tier 0 code):

```
Sensor  → Brain      : {"type":"accel","s":[[ax,ay,az], ...]}     # WS (phone) or BLE notify (ESP32)
Brain   → Actuator   : {"type":"breathe","action":"start|stop","inhale":4,"exhale":6}
Brain   → Dashboard  : {"type":"state","prob":0.0-1.0,"triggered":bool, ...}
```

Phone speaks it over WebSocket. ESP32 will speak it over BLE via a laptop bridge (`bleak`) that feeds the **same** `StreamProcessor`. The ML pipeline and the brain never know or care which one is upstream.

---

## 1. Scope — three tiers, cut from the bottom if behind

### 🟢 MVP — must be true at the demo (target: done by hour 12)
- Phone streams wrist motion → laptop classifies agitation in real time.
- Sustained agitation (persistence + hysteresis) **auto-triggers** the paced-breathing pacer — no user action.
- Pacer delivers the intervention: visual + vibration (Android) + audio swell.
- Live dashboard shows the agitation timeline and the trigger firing.
- **Safety layer exists**: risk-language screening → visible 988 handoff (mocked, never a real dial).

### 🟡 Target — the real story (hour 12–20)
- **Real hardware in the loop**: ESP32 + MPU6050 wristband streaming over BLE behind the same contract; coin-motor/LRA haptic on the wrist.
- **Claude in the loop**: reasoning chooses the response; ElevenLabs voice grounds the user ("let's breathe together…").
- **Real data**: record calm/agitated motion from the team, retrain, replace synthetic model.
- **Plush**: 2 ear motors mirror the user's state (embodied feedback); plush is holdable.

### 🔵 Stretch — if the team is flying (hour 20+)
- **Per-person calibration**: 30-second baseline capture on wear → personalized thresholds.
- **Plush voice on-device**: I2S mic + speaker in the plush, not the laptop.
- **Two-way voice conversation** with Claude during an episode, not just canned lines.
- **Second signal** to fight the freezing/stillness blind spot (e.g., phone-camera PPG heart rate, or ESP32 + heart-rate sensor).

---

## 2. Team & workstreams

Four owners, one lane each. Pair up at integration seams.

| Lane | Owner | Owns | Definition of done |
|------|-------|------|--------------------|
| **SENSE** | P1 (firmware/HW) | ESP32 firmware, MPU6050, BLE, haptic driver, `bleak` bridge | Real wristband streams accel + buzzes on command, behind the contract |
| **BRAIN** | P2 (ML) | Feature pipeline, classifier, real-data capture, personalization | Real-time prob is stable + honest; retrained on team data |
| **ACT** | P3 (orchestration + embodiment) | Claude reasoning, ElevenLabs voice, safety/988, plush build + motors | Trigger → voice + plush + safety pathway all fire |
| **GLUE** | P4 (integration/demo) | Dashboard, end-to-end wiring, demo script, backup video, poster | One-command demo runs; recorded fallback exists |

**Rule:** the contract is frozen after hour 2. Any change to it is a whole-team decision, because it breaks everyone's parallel work.

---

## 3. Hour-by-hour timeline (T+0 = sprint start)

Assumes ~20 effective hours (setup, food, a short sleep rotation). "Hardware arrives" is an **event, not a phase** — when it lands, P1 pivots to firmware and the rest keep moving.

| Block | Everyone | SENSE (P1) | BRAIN (P2) | ACT (P3) | GLUE (P4) |
|-------|----------|-----------|-----------|----------|-----------|
| **T+0–2 · Lock** | Architecture + contract frozen, repo + roles set, **Tier 0 loop running on a real phone**, agree the demo win-condition | Flash toolchain ready; write ESP32 sketch against contract using *fake* accel; design haptic circuit | Confirm pipeline on live phone data; define feature set + trigger knobs | Stand up brain server; stub Claude + ElevenLabs calls | Dashboard skeleton subscribing to `state` |
| **T+2–8 · Parallel foundations (software-first)** | Daily-standup at T+5 (15 min) | Firmware complete in sim; `bleak` bridge written + tested against fake ESP32 | Real Claude reasoning loop; safety-layer classifier for risk language | ElevenLabs TTS wired; canned grounding lines; **start plush physical build** | Agitation timeline + state view; plush-state mirror in UI |
| **T+8–14 · Hardware integration + real data** | Integrate as parts land | **When parts arrive:** flash ESP32, wire MPU6050 + haptic, bring up BLE, connect bridge | **Record team calm/agitated data**, retrain, validate against synthetic fallback | Wire plush ear motors; sync ears to trigger state; safety → 988 handoff UI | Full-loop integration on real hardware behind dashboard |
| **T+14–18 · Make it real** | Full loop on hardware end-to-end | Haptic feel tuning (LRA/DRV2605 or PWM); battery/mount for wear | Personalization / baseline calibration (stretch); threshold tuning | Claude voice conversation polish; safety hardening | Polish dashboard; write + storyboard demo |
| **T+18–20 · Demo build** | Freeze features | Wristband demo-ready + spare | Lock the model; no more retrains | Rehearse the intervention beat | **Record backup video**; build poster/slides |
| **T+20–24 · Lock + rest** | **Feature freeze at T+20.** Rehearse demo 3×. Sleep rotation. Only bug-fixes. | | | | Final run-throughs; submit |

---

## 4. Hardware — bill of materials (for when parts land)

| Component | Part | Notes |
|-----------|------|-------|
| MCU ×2 | ESP32 dev board | one wrist, one plush |
| IMU | MPU6050 (6-axis, I2C) | onboard-IMU board removes this if used |
| Wrist haptic | Coin motor **or** LRA + DRV2605L driver | DRV2605 = far smoother "breathing" feel |
| Motor driver (if coin motor) | 2N2222 transistor + flyback diode | protect the GPIO |
| Plush ears ×2 | Micro-servo or vibration motor | expressive state |
| Plush audio (stretch) | MAX98357A I2S amp + speaker, INMP441 I2S mic | MVP: use laptop audio |
| Power | 3.7V LiPo + TP4056 charger | USB power is fine for the demo |
| Wearable | wrist strap, protoboard, wire, plush toy | |

**Firmware plan (ESP32 / Arduino):** read MPU6050 over I2C → batch samples → **BLE notify** characteristic (matches the `accel` message). A **write** characteristic receives `breathe` commands → drive haptic via `LEDC` PWM or DRV2605 over I2C. Laptop `bleak` bridge subscribes to notify, feeds the existing `StreamProcessor`, and writes breathe commands back. **Zero pipeline changes.**

**BLE-flaky-floor fallback:** ESP32 over **USB serial** to the laptop (same message format). Wired is more reliable in a congested 2.4 GHz room.

---

## 5. Safety layer — non-negotiable, build it early

Any tool inserting itself into acute distress must fail safe.
- Screen all user language (typed or transcribed) for risk markers → route to **988**.
- In the demo, **mock the handoff** (show the screen + the routing decision). **Never place a real call.**
- Build it in Phase 1, not bolted on at the end — it's both the ethical floor and a credibility win with judges.

---

## 6. Demo script (what judges see — ~3 min)

1. **Baseline:** wristband on, dashboard calm, bar low.
2. **Rising agitation:** shake/act it out → bar climbs and *persists* across windows (show the false-positive guard: one twitch doesn't fire).
3. **Auto-trigger:** no button pressed → wrist buzzes a slow breathing rhythm, plush ears respond, Claude's voice: *"I've got you — let's breathe out together, slow…"*
4. **Safety:** enter risk language → safety layer flags → **988 handoff shown**.
5. **Stand-down:** hold still → system de-escalates on its own.
6. **Close:** the thesis (zero-friction, in-the-moment somatic co-regulation) + honest caveats (synthetic-trained classifier, motion is a proxy, personalization not yet validated).

Keep a **recorded backup video** of the full loop — never demo live without one.

---

## 7. Risk register + mitigations

| Risk | Mitigation (mostly pre-baked into the architecture) |
|------|------|
| Hardware arrives late / never | Phone Tier 0 is a complete demo on its own |
| BLE unstable on the floor | USB-serial tether fallback; or demo on phone |
| iPhone has no web vibration | Use an Android phone, or the real wristband, for the haptic beat |
| ElevenLabs latency/quota | Pre-generate + cache grounding lines; text fallback |
| Real-data model worse than synthetic | Keep synthetic model as fallback; personalization is stretch, not MVP |
| Team fatigue | Sleep rotation; hard feature-freeze at T+20 |

**Cut-line order if behind (drop from the top):** plush on-device audio → personalization → real hardware → live voice conversation. Each cut still leaves a coherent, honest demo.

---

## 8. Definition of done (per component)

- [ ] **SENSE** — real wristband streams accel + buzzes on command, behind the contract
- [ ] **BRAIN** — real-time probability is stable; retrained on team data; trigger is persistence + hysteresis gated
- [ ] **ACT** — trigger fires voice + plush + safety pathway; cadence ≈ 6 breaths/min, longer exhale
- [ ] **SAFETY** — risk language → visible 988 handoff (mocked)
- [ ] **GLUE** — one-command end-to-end demo runs; backup video recorded; poster done

---

*Starting point already built + verified: `pipeline.py` (sense + Random Forest), `server.py` (brain + HTTPS/WS + self-signed cert), `static/index.html` (phone sensor + pacer). See `README.md` to run it.*
