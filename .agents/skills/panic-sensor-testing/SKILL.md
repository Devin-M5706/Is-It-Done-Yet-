---
name: panic-sensor-browser-testing
description: Test the HTTPS motion-streaming app on desktop, with explicitly authorized sensor mocks.
---

# Runtime setup
- Check for an existing listener on 8443 before starting another server.
- Reuse `.venv/bin/python server.py` from the repo root; dependencies are in requirements.txt.
- Server trains its synthetic classifier at boot and generates ignored cert.pem/key.pem files.
- Open https://localhost:8443 and accept the expected self-signed certificate warning.
- No authentication is required. WebSocket connects only after clicking Start.

# Desktop coverage
- Desktop Chrome may expose DeviceMotionEvent but supply no real samples. A connected socket is not evidence of working motion sensing.
- Test breathing should animate without sensor input; capture circle size changes, not just phase text.
- Test at least one stop/restart cycle: a circle can change text without changing geometry.
- Inspect punctuation visually and document.characterSet if UTF-8 content looks corrupted.

# Authorized synthetic motion
Only mock when the user permits it. Dispatch DeviceMotionEvent on window at 50 Hz with accelerationIncludingGravity, rather than overriding handlers or the classifier. This preserves browser batching, real WSS, server inference and commands.
- Calm: coherent 0.3 Hz sine amplitudes [0.04,0.032,0.024] plus offset [0.1,0.2,0.3].
- Agitated: 5 Hz sine amplitudes [0.8,0.7,0.6], phases [0,1,2], same offsets.
- Allow 8–10 seconds per mode. Capture actual WS state/breathe messages using an additional message listener.
- Verify four qualifying windows precede trigger/release, according to current pipeline constants.
- Clear synthetic timers afterward. Label evidence tested-against-mocks; this does not validate phone permissions, sensor units/sample rate, clinical accuracy, vibration or audible output.

## Devin Secrets Needed
None for local testing.
