"""
Tier 0 panic co-regulation loop -- laptop "brain".

Phone (strapped to wrist) opens the served page over HTTPS, streams its
accelerometer over a WebSocket. This server runs the sense pipeline and, when
agitation is sustained, tells the phone to start the paced-breathing pacer.
No microcontroller, no ESP32 -- the phone is the sensor + the haptic.

Run:  python server.py
Then open  https://<your-lan-ip>:8443  on the phone (accept the cert warning).
"""

import argparse
import asyncio
import datetime
import ipaddress
import json
import pathlib
import secrets
import socket
import ssl
import time

from aiohttp import WSMsgType, web

from pipeline import Classifier, StreamProcessor

# breathing cadence: ~6 breaths/min, longer exhale (net parasympathetic shift)
INHALE = 4.0
EXHALE = 6.0

HERE = pathlib.Path(__file__).parent
STATIC = HERE / "static"
PORT = 8443

CLF = Classifier()
CAPTURE = False  # --capture: record every accel frame, even unlabeled


def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def ensure_cert(lan_ip):
    """Create a self-signed cert once. DeviceMotion needs a secure context;
    a self-signed cert works after you tap through the browser warning."""
    cert_p, key_p = HERE / "cert.pem", HERE / "key.pem"
    if cert_p.exists() and key_p.exists():
        return cert_p, key_p

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "panic-sensor-tier0")])
    san = [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
    try:
        san.append(x509.IPAddress(ipaddress.ip_address(lan_ip)))
    except ValueError:
        pass
    now = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .sign(key, hashes.SHA256())
    )
    cert_p.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_p.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))
    return cert_p, key_p


def print_bar(prob, triggered):
    n = int(prob * 30)
    bar = "#" * n + "-" * (30 - n)
    flag = "  << BREATHING TRIGGERED" if triggered else ""
    print(f"\ragitation [{bar}] {prob:0.2f}{flag}   ", end="", flush=True)


async def index(request):
    return web.FileResponse(STATIC / "index.html")


async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    proc = StreamProcessor(CLF)
    session_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
    label = None
    rec_path = HERE / "data" / "raw" / f"{session_id}.jsonl"
    rec_f = None
    print("\n[+] phone connected")
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            data = json.loads(msg.data)
            if data.get("type") == "label":
                value = data.get("value")
                label = value if value in ("calm", "agitated") else None
                print(f"\n[rec] label={label}")
                continue
            if data.get("type") != "accel":
                continue
            rec_label = label if label is not None else ("none" if CAPTURE else None)
            if rec_label is not None:
                if rec_f is None:
                    rec_path.parent.mkdir(parents=True, exist_ok=True)
                    rec_f = open(rec_path, "a")
                rec_f.write(json.dumps(
                    {"t": int(time.time() * 1000), "label": rec_label, "s": data["s"]}
                ) + "\n")
                rec_f.flush()
            for ax, ay, az in data["s"]:
                ev = proc.add(ax, ay, az)
                if ev is None:
                    continue
                print_bar(ev["prob"], ev["triggered"])
                await ws.send_json({"type": "state", "prob": ev["prob"],
                                    "triggered": ev["triggered"]})
                if ev["trigger_changed"]:
                    if ev["triggered"]:
                        await ws.send_json({"type": "breathe", "action": "start",
                                            "inhale": INHALE, "exhale": EXHALE})
                    else:
                        await ws.send_json({"type": "breathe", "action": "stop"})
    finally:
        if rec_f is not None:
            rec_f.close()
    print("\n[-] phone disconnected")
    return ws


def main():
    global CAPTURE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true",
                        help="record all accel frames to data/raw "
                             "(label 'none' when unlabeled); otherwise only "
                             "labeled frames are written")
    CAPTURE = parser.parse_args().capture

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/ws", ws_handler)
    app.router.add_static("/static", STATIC)

    lan_ip = get_lan_ip()
    cert_p, key_p = ensure_cert(lan_ip)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_p, key_p)

    print("=" * 56)
    print(f"  {CLF.describe()}")
    print(f"  Open on your phone:  https://{lan_ip}:{PORT}")
    print("  (accept the certificate warning -- it's self-signed)")
    print("=" * 56)
    web.run_app(app, host="0.0.0.0", port=PORT, ssl_context=ctx, print=None)


if __name__ == "__main__":
    main()
