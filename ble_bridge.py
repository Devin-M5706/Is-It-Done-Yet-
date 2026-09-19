"""
BLE bridge: ESP32 wristband -> the SAME sense pipeline the phone uses.

Connects to the wristband over BLE, feeds its accelerometer notifications into
StreamProcessor (identical logic to server.py), and writes paced-breathing
commands back to the haptic. This is the "one contract, two sensor sources"
swap: pipeline + trigger logic unchanged, only the transport differs.

STATUS: UNTESTED against hardware. We don't have the ESP32 yet, so this has
never run for real. The UUIDs and packet layout match firmware/wristband/
wristband.ino by construction, but treat this as a bench starting point, not a
proven module. Needs:  pip install bleak

Run:  python ble_bridge.py            # scan for a device named "panic-wrist"
      python ble_bridge.py <ADDRESS>  # connect directly
"""

import asyncio
import struct
import sys

from bleak import BleakClient, BleakScanner

from pipeline import Classifier, StreamProcessor

DEVICE_NAME = "panic-wrist"
ACCEL_CHAR = "9a0b0002-1e3c-4f5a-9b2d-8c7e6f5a4b3c"    # notify (int16 milli-g triples)
BREATHE_CHAR = "9a0b0003-1e3c-4f5a-9b2d-8c7e6f5a4b3c"  # write  [action, inhale, exhale]
INHALE, EXHALE = 4, 6


def bar(prob, trig):
    n = int(prob * 30)
    tail = "  << BREATHING" if trig else "             "
    print(f"\ragitation [{'#' * n}{'-' * (30 - n)}] {prob:0.2f}{tail}",
          end="", flush=True)


async def main():
    clf = Classifier()
    proc = StreamProcessor(clf)

    addr = sys.argv[1] if len(sys.argv) > 1 else None
    if addr is None:
        print(f"scanning for '{DEVICE_NAME}' ...")
        dev = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10)
        if dev is None:
            print("not found. Is the wristband powered and advertising?")
            print("Tip: point claude-code-eyes at the board's LED to confirm it's on.")
            return
        addr = dev.address

    loop = asyncio.get_running_loop()
    outq = asyncio.Queue()

    async with BleakClient(addr) as client:
        print(f"connected to {addr}  (model: {clf.source})")

        def on_accel(_, data):
            # packet = N samples x (int16 ax, ay, az) little-endian, milli-g
            n = len(data) // 6
            if n == 0:
                return
            vals = struct.unpack("<" + "h" * (3 * n), bytes(data[: 6 * n]))
            for i in range(n):
                ax, ay, az = (v / 1000.0 for v in vals[i * 3:i * 3 + 3])
                ev = proc.add(ax, ay, az)
                if ev is None:
                    continue
                bar(ev["prob"], ev["triggered"])
                if ev["trigger_changed"]:
                    pkt = struct.pack("BBB", 1 if ev["triggered"] else 0,
                                      INHALE, EXHALE)
                    loop.call_soon_threadsafe(outq.put_nowait, pkt)

        async def writer():
            while True:
                pkt = await outq.get()
                try:
                    await client.write_gatt_char(BREATHE_CHAR, pkt, response=False)
                except Exception as e:
                    print(f"\n[warn] breathe write failed: {e}")

        await client.start_notify(ACCEL_CHAR, on_accel)
        wtask = asyncio.create_task(writer())
        print("streaming. Ctrl-C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        finally:
            wtask.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye")
