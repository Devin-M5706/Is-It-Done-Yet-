---
name: esp32-firmware
description: How to write, build, and verify ESP32 firmware for this project's wristband/plush and keep it on the BLE contract (firmware/, ble_bridge.py).
---

# ESP32 firmware (wristband + plush)

Sketches live in `firmware/wristband/main.cpp` and `firmware/plush/main.cpp`.
The laptop side is `ble_bridge.py`. Contract reference: `ARCHITECTURE.md` §2.

## The contract (do not drift)

UUID suffix for everything: `-1e3c-4f5a-9b2d-8c7e6f5a4b3c`.

| Device (BLE name) | Service | Char | Prop | Payload |
|---|---|---|---|---|
| wristband `panic-wrist` | `9a0b0001-…` | ACCEL `9a0b0002-…` | NOTIFY + BLE2902 | `SAMPLES_PER_PACKET` (4) × `int16 ax,ay,az` LE, **milli-g** = 24 bytes |
| wristband `panic-wrist` | `9a0b0001-…` | BREATHE `9a0b0003-…` | WRITE | 3 bytes `[action 0=stop/1=start, inhale_s, exhale_s]`; bridge sends `[1,4,6]` / `[0,4,6]` |
| plush `panic-plush` | `9a0b1001-…` | STATE `9a0b1002-…` | WRITE | 4 bytes `[mode 0..3, heartbeat_bpm, breathe_phase 0/1, secs]` |

- milli-g conversion: `(int16_t)(raw / LSB_PER_G * 1000.0f)`, `LSB_PER_G = 16384.0f` (MPU6050 ±2 g). Bridge divides by 1000 → g.
- The bridge derives sample count from payload length (`len // 6`), so fewer samples per packet is contract-compatible; a different sample width, byte order, or unit is not.
- Any contract change (UUID, layout, units, byte order, packet size semantics) MUST land in the same PR as matching edits to `ble_bridge.py` and `ARCHITECTURE.md` §2.

## Build / flash / monitor

PlatformIO (compile check works without hardware; CI runs it via `.github/workflows/firmware.yml`):

```bash
pip install platformio
cd firmware
pio run                          # both envs
pio run -e wristband             # or -e plush
pio run -e wristband -t upload   # board on USB
pio device monitor -b 115200
```

Arduino IDE equivalent: Boards Manager → install **esp32** (Espressif); board **"ESP32 Dev Module"**;
copy `wristband/main.cpp` to a separate sketch folder `~/Arduino/wristband/wristband.ino` (folder name must equal
sketch name; never place the `.ino` next to `main.cpp` or the IDE compiles both → duplicate `setup()`/`loop()`) and open it;
plush additionally needs the **ESP32Servo** library. Wristband needs no external libraries
(`BLEDevice`, `Wire` ship with the core). Keep `#include <Arduino.h>` — harmless in the IDE, required for PlatformIO.

`firmware/platformio.ini`: `src_dir = .`, one env per sketch selected with `build_src_filter = +<wristband/>` / `+<plush/>`;
`lib_deps = madhephaestus/ESP32Servo` on the plush env only. Sources must be `main.cpp` (PlatformIO only auto-converts `.ino` at the `src_dir` root).

## Conventions (match the existing sketches)

- MPU6050 via raw I2C registers, no library: `Wire.begin(PIN_SDA, PIN_SCL)`, write `0x6B ← 0x00` to wake, burst-read 6 bytes from `0x3B` (`ACCEL_XOUT_H`), high byte first.
- Haptic / heartbeat motor via LEDC PWM: `ledcSetup(ch, 20000, 8)`, `ledcAttachPin(pin, ch)`, `ledcWrite(ch, 0..255)`.
- NOTIFY characteristics get `addDescriptor(new BLE2902())` or centrals cannot subscribe.
- Non-blocking `loop()`: sample when `micros() - lastSampleUs >= SAMPLE_US` and advance `lastSampleUs += SAMPLE_US` (no `delay()` in the sampling path). `SAMPLE_HZ = 50` matches `pipeline.py` `FS`.
- State written from BLE callbacks is `volatile` (`deviceConnected`, `breatheOn`, `inhaleS`, `exhaleS`, `mode`, `heartBpm`); callbacks only set flags, `loop()` acts on them.
- On disconnect: clear flags, stop the motor, `s->getAdvertising()->start()` so the bridge can reconnect.
- Pin constants at the top of the file, `static const int`, in a block marked `EXAMPLE`; keep `SVC_UUID`/`*_UUID` as `#define`s next to them.
- Keep "STATUS: UNTESTED" headers honest: update them only after a real board has run the code.

## Pitfalls

- ESP32 GPIO is **3.3 V only**. Never feed 5 V logic or sensor outputs into a pin.
- Servos (plush ears) run from a **separate 5 V rail**, common ground; the 3V3 regulator cannot supply them.
- Motors go through a transistor (2N2222 base via ~1 kΩ) with a **flyback diode** across the motor; never drive a motor from a GPIO directly.
- **BLE MTU:** default ATT MTU is 23 → **20-byte** notify payload. The ACCEL packet is **24 bytes**. Without MTU negotiation the stack truncates the notify and the bridge silently sees 3 samples instead of 4 (`len // 6`), i.e. a 25 % sample drop, no error. Linux/BlueZ, macOS and Windows centrals normally negotiate a larger MTU, so this usually works, but it is unverified on hardware. If the bridge logs fewer samples than expected: set `SAMPLES_PER_PACKET = 3` (18 bytes; bridge unaffected) or call `BLEDevice::setMTU(64)` before `createServer()` and confirm the negotiated MTU. Do not exceed 20 bytes for any new notify characteristic unless you have verified the MTU.
- iOS lacking a web Vibration API is a phone-page limitation only; it is irrelevant to firmware.
- Don't `delay()` inside BLE callbacks; they run on the BLE task.

## Test

Without hardware: `cd firmware && pio run` must succeed for both envs (this is what CI checks).

With hardware:
1. Flash: `pio run -e wristband -t upload`, then `pio device monitor -b 115200` to confirm boot (no boot loop, no I2C errors).
2. `pip install bleak && python ble_bridge.py` (scans for `panic-wrist`; or pass the address). It prints `connected to <addr>` then a live `agitation [####----] 0.xx` bar.
3. Still wrist ≈ low bar; vigorous shake for ~2–3 s ≈ high bar and `<< BREATHING`; hold still ≈ stands down and the haptic stops.
4. If still ≠ low or values look wrong: check `LSB_PER_G` matches the configured full-scale range (16384 for ±2 g), the high/low byte order in `readAccel`, and the `int16` little-endian packing in `pktBuf` versus `struct.unpack("<h...")` in the bridge.
5. Plush: there is no brain-side writer yet; test with a BLE tool (e.g. nRF Connect) writing 4 bytes to `9a0b1002-…`, e.g. `02 3C 00 00` → ears breathe, heartbeat at 60 bpm.
