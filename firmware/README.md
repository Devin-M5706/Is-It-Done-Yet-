# Firmware (ESP32) — boilerplate, UNTESTED

> **Status: skeleton, not verified on hardware.** We don't have the ESP32s yet,
> so none of this has run on a real board. It's written against the datasheets
> and the project's message contract so it *drops into* the existing laptop
> pipeline (`ble_bridge.py`) with zero changes — but treat it as a bench starting
> point and expect to tune pins, I2C, and timing. **No performance or timing
> numbers are claimed.**

Two sketches, both speaking the same contract as the Python side:

| Sketch | Board role | Talks to |
|--------|-----------|----------|
| `wristband/main.cpp` | MPU6050 → BLE accel stream; BLE breathe cmd → haptic | `ble_bridge.py` |
| `plush/main.cpp` | BLE plush-state → 2 ear servos + heartbeat motor | brain (to be wired) |

## BLE contract (matches `ble_bridge.py`)

**Wristband** — service `9a0b0001-…`
- `ACCEL` `9a0b0002-…` **NOTIFY**: N samples × `int16(ax,ay,az)` little-endian, **milli-g** (4 samples/packet = 24 bytes)
- `BREATHE` `9a0b0003-…` **WRITE**: 3 bytes `[action(0/1), inhale_s, exhale_s]`

**Plush** — service `9a0b1001-…`
- `STATE` `9a0b1002-…` **WRITE**: 4 bytes `[mode(0..3), heartbeat_bpm, breathe_phase(0/1), secs]`

## Toolchain

- **Arduino IDE** → Board Manager → install **esp32** (Espressif). Board: *ESP32 Dev Module*.
- Wristband: **no external libraries** — uses built-in `BLEDevice`/`Wire`; the MPU6050 is read via raw I2C registers.
- Plush: install the **ESP32Servo** library.

### PlatformIO (compile check without hardware)

```bash
pip install platformio
cd firmware && pio run
pio run -e wristband -t upload
pio device monitor -b 115200
```

PlatformIO's source discovery requires `main.cpp` in each environment
directory (it only auto-converts `.ino` files at the `src_dir` root), so the
sketches are named `wristband/main.cpp` and `plush/main.cpp` with an explicit
`#include <Arduino.h>`. To open either in Arduino IDE, copy `main.cpp` to
`<folder>/<folder>.ino` (e.g. `wristband/wristband.ino`); the code is otherwise
identical. CI runs `pio run` for both envs on every change under `firmware/`
(`.github/workflows/firmware.yml`).

## Wiring (EXAMPLE pins — change to match the sketches / your board)

**Wristband**
- MPU6050: `SDA→GPIO21`, `SCL→GPIO22`, `VCC→3V3`, `GND→GND`
- Haptic: `GPIO25 → transistor (2N2222) base via ~1kΩ`; motor across collector→GND with a **flyback diode**; motor + rail to VBAT. (Or a DRV2605L over I2C for a smoother "breathing" feel — not wired in this skeleton.)

**Plush**
- Ear servos: signal `GPIO18` / `GPIO19`, power from a **separate 5V rail** (not the ESP32 3V3), grounds common.
- Heartbeat motor: `GPIO25 → transistor` as above.

⚠️ **Never put 5V on a 3.3V-only ESP32 pin.** Check rails and polarity before power-on.

## Flash

1. PlatformIO: `cd firmware && pio run -e wristband -t upload` (or `-e plush`).
   Arduino IDE: copy `wristband/main.cpp` to `wristband/wristband.ino` (folder name must
   match), open it, select the board + serial port, upload.
2. After upload, the wristband advertises as **`panic-wrist`**, plush as **`panic-plush`**.
3. On the laptop: `python ble_bridge.py` (scans for `panic-wrist`).

## Verify before you trust it

- Use **claude-code-eyes** (point an IP Webcam at the bench) to check the wiring
  and confirm the board's LED / any display before power-on and while it runs.
- Sanity-check the accel stream in `ble_bridge.py`'s live bar: still wrist ≈ low,
  vigorous shake ≈ high. If axes look swapped or scaled wrong, fix `LSB_PER_G` /
  the packing in `wristband/main.cpp` first.
