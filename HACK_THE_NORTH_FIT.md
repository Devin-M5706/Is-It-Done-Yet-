# Hack the North — Judging Fit & Strategy

Scoring the passive panic co-regulation system against HtN's actual criteria — and the one strategic pivot the criteria demand.

---

## ⚠️ The pivot the criteria force on you

HtN says, in writing:

> **Practicality & entrepreneurship is a NON-criterion.** "A project *does not* need to be useful or solve a real-world problem to be successful."

Your project's most *obvious* strength — "this genuinely helps people in a mental-health crisis" — is **not scored.** It doesn't hurt you, but every minute you spend selling *usefulness* is a minute not spent on what actually wins: **WOW, technical depth, originality, design.**

**So reallocate the pitch.** Lead with the *experience* and the *engineering*, not the *cause*. The cause is the setting; the WOW is the machine.

Same trap on the other non-criterion: **Visual appeal ≠ Design.** A pretty dashboard earns nothing. An *intuitive, considered interaction* earns points. Your design story is the interaction, not the gradient.

---

## Scorecard

| Criterion | Fit | One-line verdict |
|-----------|-----|------------------|
| ⭐ WOW factor | **High (if demoed physically)** | The "it knew before I said anything" moment is a real jaw-drop — but only if it's *felt*, not shown on a chart |
| 🧠 Technical ability | **High** | Spans embedded + BLE + real-time DSP/ML + multi-agent AI + safety NLP — few teams cover this range |
| 💡 Originality | **Medium–High** | Anxiety tools are a crowded hackathon lane; your novelty is *passive + embodied*, not the topic |
| 🎨 Design | **Medium (strong contrarian angle)** | "The best UI for a panic attack is no UI" is a sophisticated thesis — if you make the invisible interaction feel intentional |

---

## ⭐ WOW factor — your biggest lever

**Why it can win:** the auto-trigger with **no button press** is genuinely surprising. A judge shakes the wristband, does nothing else, and the system *reacts on its own* — the wrist breathes, the plush stirs, a voice arrives. That "it noticed me" beat is the WOW.

**Why it can flop:** if the demo is a probability bar climbing on a laptop, there is no WOW. Charts don't wow. **Bodies wow.**

**Moves to max it:**
- Make the trigger moment **theatrical and physical**. Hand the judge the plush. Let *them* trigger it by fidgeting. The WOW is *their* body, not your slide.
- Nail the timing: the gap between "sustained agitation" and "the plush responds" should feel like being noticed, not like a loading spinner. Tune `K_TRIGGER` so it's fast enough to feel alive.
- One perfect sensory beat > five features. The buzz + plush + voice landing together in ~1 second is the whole demo.
- Kill the "so what": open with the loop working, not with statistics about panic attacks.

---

## 🧠 Technical ability — your quiet strength

**Why it scores:** this is a rare full-stack-of-disciplines build:
- **Embedded / firmware** — ESP32, MPU6050 over I2C, BLE GATT, haptic driver
- **Real-time DSP + ML** — smoothing, overlapping windows, FFT/PSD band powers, skew/kurtosis, inter-axis correlation, Random Forest, persistence + hysteresis
- **Multi-agent AI** — Claude reasoning + ElevenLabs voice I/O
- **Safety NLP** — risk-language screening → 988 routing
- **Distributed systems** — multi-device loop over one contract

Most teams do *one* of these. You're doing five. Judges reward depth **and** the "we learned something new" arc HtN explicitly calls out.

**Moves to max it:**
- **Show the internals**, briefly: a live feature view or feature-importances plot proves it's real ML, not an `if accel > threshold`. This is the difference between "impressive" and "a wrapper."
- Get **real data** off your own wrists and retrain — "trained on data we captured tonight" beats "synthetic" every time a judge asks.
- Name the hard new thing you learned (BLE bring-up, on-edge inference, sensor DSP). That sentence directly hits the criterion.
- **Honesty is technical credibility.** Say "synthetic-trained, motion is a proxy, some panic presents as freezing" — sophisticated judges trust teams who know their system's limits.

**Risk to manage:** if all a judge sees is "random forest on accelerometer → threshold," it reads shallow. Surface the DSP + persistence logic + firmware so the depth is visible.

---

## 💡 Originality — protect this one

**The risk:** "anxiety detector + breathing app" is one of the most common hackathon genres. A judge on their 40th project may pattern-match you to it in five seconds.

**Your actual novelty (make it unmistakable):**
- **Passive, action-free.** Every other tool needs the user to open an app during the exact moment their executive function has collapsed. Yours needs *nothing*. That inversion is the original idea.
- **Embodied, not on a screen.** Co-regulation through a physical plush + haptic touch, not a chatbot. "Two physical objects, one loop."
- **Entrainment through touch, not instruction.** You don't tell a panicking brain to breathe — you give its body a rhythm to sync to.

**Moves to max it:**
- Say the anti-pitch out loud: *"This is not another anxiety app. There's no app to open — that's the whole point."* Preempt the pattern-match.
- Frame the axis of novelty as **passive + embodied**, so judges file you somewhere new.

---

## 🎨 Design — win it with a contrarian thesis

**Your design argument is strong *if you make it explicit*:**

> "The best interface during a panic attack is *no interface*. The person can't tap through screens — so the interaction is a rhythm they feel, and a thing they hold."

That's a genuine, defensible UX position — but only if the *invisible* interaction feels **designed**, not accidental.

**Moves to max it:**
- Design the **non-visual** interaction deliberately: the haptic cadence, how the plush escalates/de-escalates, what "putting it on" feels like, how it stands down. Treat the rhythm as your primary UI and be able to explain the choices.
- The one screen judges *do* see (dashboard) should be clean and legible — but frame it as the **observer/clinician view**, not the user's interface. That reframing turns "there's no app UI" from a gap into a thesis.
- Have a **tangible, considered artifact** — a real plush, a real wristband — so "design" isn't invisible. HtN wants intuitive + engaging for the target audience; the target audience's device is the plush.

---

## The 3-minute pitch, re-weighted for HtN

1. **(0:00) Cold open — the WOW.** Judge fidgets the band; system reacts unprompted. No preamble. *(WOW)*
2. **(0:40) The inversion.** "No app to open — that's the point. Passive, embodied." *(Originality)*
3. **(1:15) Lift the hood.** Live features → RF → persistence trigger → BLE → plush; "here's the hard thing we learned." *(Technical)*
4. **(2:10) The design thesis.** "The interface is a rhythm you feel." + the safety floor (988). *(Design + credibility)*
5. **(2:40) Honest close.** Synthetic-trained, motion is a proxy — "here's what's real and what's next." *(Technical credibility)*

Note what's **absent**: a slide about how big the mental-health market is, or how many people have panic attacks. That's the non-criterion. Cut it.

---

## Honest weaknesses a sharp judge will probe

- **"Isn't this just a threshold on accelerometer data?"** → counter with the DSP + persistence + real-data + personalization story. Have the feature view ready.
- **"Motion misses freezing-type panic."** → agree openly; name it as known future work (second signal / PPG). Owning it beats getting caught.
- **"I've seen breathing apps before."** → the passive + embodied inversion; you are not an app.
- **"The plush is a toy, not tech."** → the plush is the *interface*; the tech is the sense→reason→act loop behind it.

---

## Bottom line

The project can score on **all four** real criteria — that's rare, and it's why it's a strong HtN pick. The single highest-leverage change isn't in the code: it's **re-pointing the pitch** away from "this is useful" (not scored) toward **WOW + technical depth + the passive/embodied originality + the no-UI design thesis** (all scored). Build the demo so the WOW is *felt in a judge's hands*, and make the engineering *visible*.
