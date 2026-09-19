# Is it good to demo? — Honest readout

**Short answer:** It's a **working skeleton you can demo today**, but it is **not yet a finalist-grade Hack the North demo** — and **nobody has watched it run on a phone yet.** Two different questions, two different answers.

---

## Q1 — Can you demo *something that works* right now?

**Basically yes.**
- Pipeline verified: calm → **0.04**, agitated → **1.00**, trigger fires on sustained motion.
- Full loop wired: phone → laptop → pacer (buzz + breathing circle + audio).
- It's a real "shake it → it notices → it breathes back" loop.

**One caveat before you trust it:** the server + cert-gen are built, but the **live end-to-end test got interrupted.** Run it on a real phone once before believing "it works."

> 5-minute smoke test: `python server.py` → open the printed URL on your phone → accept cert → Start → shake it → confirm the buzz + breathing circle fire. Until you've *seen* that, "it works" is a claim, not a fact.

---

## Q2 — Is it good enough to *score* at HtN as-is?

**Not yet.** Mapped to the actual criteria:

| Criterion | State now | Why it falls short |
|-----------|-----------|--------------------|
| ⭐ **WOW** | Weak | Right now the WOW is "a phone buzzes." Fine as *tech*, middling as *WOW*. The jaw-drop needs the **plush reacting** / a **wristband** so the judge feels "it noticed me" in their hands — not on a laptop. |
| 🧠 **Technical** | Hidden | The DSP/ML depth is in the code but **invisible** in the demo — a judge just sees a bar move. Needs a **live feature view** and ideally **real captured data**, or it reads as "threshold on accelerometer." |
| 💡 **Originality** | At risk | Without the physical plush it looks like "a breathing app" — the exact crowded lane you need to escape. |
| 🎨 **Design** | Incomplete | The "no-UI" thesis only lands with a **tangible artifact** to hold. |

---

## The framing that matters

> **Tier 0 is your insurance policy, not your pitch.**

- **Insurance:** guarantees you walk in with a working loop no matter what happens with parts, Wi-Fi, or sleep.
- **Pitch:** the demo that actually competes = Tier 0 **+ real hardware + the plush + visible ML**. That's exactly what the sprint plan front-loads.

Don't demo the insurance policy and call it the pitch.

---

## What to do next (in order)

1. **Run the 5-minute live phone test.** Verify the floor before building on it.
2. **Add data-capture mode** → record labeled calm/agitated windows tonight → retrain → "trained on real data we caught tonight" (huge for Technical).
3. **Get the plush + wristband in the loop** → this is what converts WOW and Originality from "neat" to "finalist."
4. **Surface the ML** → a live feature / feature-importance view so the depth is *visible*, not just present.

**Do #1 first.** Verify the floor before you build on it.
