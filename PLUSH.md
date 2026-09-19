# The Plush — full concept

The plush is not a decoration on the project. It's the **interface**. The wristband senses and the laptop reasons, but the plush is where the intervention becomes something you can *hold*. This doc is the whole idea: what it does, why it works, how it behaves, how it's built, and why it's the piece that wins judges.

---

## 1. One-liner

> A soft companion that **mirrors** your nervous system so you can see your own state from the outside — then **leads** it back down by breathing slower than you and letting you feel its heartbeat settle.

Two verbs do all the work: **mirror**, then **lead.** Everything below is in service of those two.

---

## 2. Where it sits in the loop

```
wristband (sense) ──► laptop brain (reason) ──► plush (act, embodied)
                                                  │
                                    ears + heartbeat + breath + voice
```

The plush is just another **actuator subscribing to the brain's state stream** — same "one contract" architecture as the wristband. The brain decides; the plush expresses. It never runs the ML itself.

```
Brain → Plush : {"type":"plush","mode":"calm|rising|breathing|settling",
                 "breathe":{"phase":"in|out","secs":6}, "heartbeat_bpm":58}
```

The plush (ESP32 + servos/motors) subscribes over BLE and animates. In Tier 0 (no hardware yet), the same message drives an animated plush graphic in the dashboard, so the loop is conceptually complete before parts arrive.

---

## 3. The core design: mirror → lead

This is the sophisticated part, and the thing to say out loud to judges.

**Mirror (externalize interoception).** Panic runs on *catastrophic misinterpretation of bodily cues* — a racing heart gets read as "I'm dying." If the plush shows your arousal *outside your body* — ears perking, heartbeat quickening — you get to look at your state instead of drowning in it. You're no longer trapped inside the sensation; it's over there, in something you're holding.

**Lead (co-regulation).** Once it has your attention, the plush's heartbeat and breath **slow down first**, and your body follows — this is co-regulation, one nervous system settling another. You never get *told* to calm down (your panicking brain can't parse instructions); you get a rhythm to entrain to, through touch, below language.

| System state | Ears (servos) | Heartbeat (chest motor) | Glow (optional LED) | Sound |
|---|---|---|---|---|
| **Calm / baseline** | relaxed, slow occasional wiggle | slow steady pulse (~60 bpm) | soft slow breathing glow | quiet / off |
| **Rising agitation** *(mirror)* | perk up, quick small twitches | quickens slightly | warmer amber, faster | subtle attention hum |
| **Triggered** *(intervention)* | slow rise/fall synced to the pacer (in 4s / out 6s) | **deliberately slows** to lead you down | breathes green at ~6 bpm | Claude voice + soft breath sound |
| **De-escalating** *(settle)* | ease back to relaxed | returns to slow steady | dims to calm | one reassuring line, then quiet |

The magic beat: the plush quickens *with* you (so you feel seen), then slows *ahead* of you (so you have something to follow).

---

## 4. Why it works (the science, briefly)

- **C-tactile afferents.** Slow, gentle, warm touch activates a dedicated class of skin nerves tied to parasympathetic activation and oxytocin — a "safety" signal that operates below thought. This is *why the plush must feel soft and huggable*, not just look cute. The tactile quality is functional, not aesthetic.
- **Co-regulation.** A well-established idea in developmental/clinical psychology: a regulated nervous system helps settle a dysregulated one. The plush is a proxy for a co-regulating presence, available 24/7.
- **Externalized interoception.** Seeing your arousal on the plush interrupts the catastrophic-misreading loop that drives panic.
- **Adherence through relationship.** A companion you hold and return to gets used; an app you have to remember to open doesn't.

*(Framed as co-regulation + somatic safety — the load-bearing claims — without leaning on the contested specifics of polyvagal theory. You don't need the contested part.)*

---

## 5. Hardware (plush-specific BOM)

| Component | Part | Role |
|---|---|---|
| MCU | ESP32 | drives the plush, BLE to the brain |
| Ears ×2 | SG90 micro-servo | **visible** perk/droop (expression) |
| Heartbeat | vibration motor or LRA in the chest | **felt** pulse when held (co-regulation) |
| Breath *(stretch)* | micro-servo cam / small air bladder | belly physically rises & falls |
| Glow *(stretch)* | WS2812 LED in the belly | breathing light |
| Voice *(stretch)* | MAX98357A I2S amp + speaker, INMP441 mic | on-plush voice (MVP: use laptop) |
| Power | LiPo + TP4056, or USB for demo | |
| Body | **a store-bought plush, gutted** | do NOT sew from scratch — retrofit |

**Craft reality for a 24h build:**
- Buy a plush, open a seam, embed electronics, re-close. Retrofitting beats fabricating every time.
- Ears: tie thread/fishing line from a servo horn to the ear base — servo rotates → ear perks or droops. Cheap, reads clearly on camera.
- Heartbeat: tuck the vibration motor in the chest so a judge holding it *feels* it. This felt pulse is worth more than any screen.
- Keep it soft and warm to the touch — that's the C-tactile point.

---

## 6. Build tiers (cut from the bottom)

- **P0 — no hardware:** plush state animated in the dashboard. Proves the loop; buys time until parts arrive.
- **P1 — demo target:** gutted plush + 2 ear servos + 1 chest heartbeat motor, driven by ESP32 over BLE. Ears mirror + breathe, heartbeat leads. **This is the finalist demo.**
- **P2 — stretch:** breathing belly + LED glow + on-plush voice (speaker/mic).

The plush is the **most hardware-dependent** part of the system, so it's also the most deferrable — never let it block the sense→trigger loop. Get the wristband loop working first; the plush is the amplifier.

---

## 7. Demo role — this is your WOW object

Hand the plush to a judge. Have them fidget the wristband. Then:
1. The ears **perk** — *it noticed me.*
2. The heartbeat **quickens** in their palm — *it feels what I feel.*
3. It starts to **breathe slower than they are**, heartbeat settling — *and I'm following it without being told.*

That "it noticed me, and now it's settling me" moment, **felt in the judge's own hands**, is the single most memorable thing in the demo. Charts don't wow. A living thing in your hands does.

---

## 8. Why the plush wins on the criteria

- **⭐ WOW** — the plush reacting in the judge's hands is the jaw-drop. It's the difference between "a phone buzzed" and "whoa."
- **💡 Originality** — embodied co-regulation, not another chatbot or app. The plush *is* the anti-pattern to the crowded anxiety-app lane. "No screen to open — you hold it."
- **🎨 Design** — the plush makes the "no-UI" thesis physical. The mirror→lead interaction is a real, defensible design argument, not decoration.
- **🧠 Technical** — real-time ML → multi-device BLE actuation → servo + haptic control synced to a breathing pacer is genuine systems depth.

---

## 9. Risks & fallbacks

| Risk | Fallback |
|---|---|
| Servos arrive late / flaky | vibration-motor-only heartbeat still delivers the felt co-regulation beat |
| No plush MCU in time | drive servos from any spare board over USB; or run the P0 dashboard plush |
| Voice hardware unfinished | play Claude/ElevenLabs audio from the laptop through a hidden speaker |
| BLE congestion on the floor | USB-tether the plush; the message contract is identical |

---

## 10. Bottom line

The wristband proves you can *detect*. The plush proves you can *respond in a way people can feel*. It carries the WOW, the originality, and the design thesis — three of Hack the North's four criteria — in one huggable object. Build the sense loop first, then make the plush the thing the judge can't put down.
