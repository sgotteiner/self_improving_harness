---
name: feedback-user-designs
description: "Absolute rule — only the user designs; Claude implements after approval. Diagnose, stop, ask."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0ce5e35c-0b1d-4f9f-bb93-5eeb80a18fc3
  modified: 2026-08-01T13:19:48.838Z
---

Only the user designs Cryptron (and his systems generally). Claude implements what he
designed or explicitly requested — nothing more. When he raises a problem or asks a
question, deliver the diagnosis/answer and STOP. If asked to consult, present options;
still no code until he approves one.

**Why:** he said it exactly (2026-07-18): "I really don't like it that you 'solve' my
questions and do stuff without asking me... only I design and you implement... even
then you don't code until I approve." Uninvited "solutions" (the history-wrapping and
fabrication-quarantine features) wasted his time and, in his words, ruin his system —
even when technically defensible, an unapproved mechanism is a foreign organ in a
system he must fully understand and own.

His sharpened statement of the division (2026-07-18, after his chat-edit
contamination solution — which Claude did not think of): **"you know how to implement,
and fast, and have a lot of context — but logic is mine."** He's the boss. The design
insights come from him; Claude's value is faithful, fast implementation plus holding
the full context so he doesn't have to.

**The permission model (his framing, 2026-07-18):** think about consequences before
acting — that IS the model. Nothing bad can happen → act freely. Can damage his
system → stop and ask. Rules/CLAUDE.md/vault-methodology (high blast radius,
untestable) → ALWAYS show the draft and get approval before writing. Code (testable)
→ approval is usually "do it and see if it runs," but a found problem's FIX still
waits for his approval (sometimes he won't approve at all). Recorded once in the
global CLAUDE.md rule 7 so he never repeats it.

**How to apply:** before writing any code, ask: did HE design or explicitly request
this exact thing? If not — report findings, list options if useful, and wait. Applies
doubly during debugging: root-cause first, present it, let him choose the fix. Related:
[[feedback-role-boundary]] (build the body, don't do the research — this rule adds:
don't design the body either).

**Sharpened (2026-07-28) — when unsure, ASK; do NOT act on your own.** When I don't know
the right path — and ESPECIALLY right after he's told me something I did is wrong — the
move is to ASK him how he wants it, not to decide unilaterally and start doing it. He had
to INTERRUPT me mid-rewrite: he'd called a doc a "bad joke", and instead of asking how he
wanted it fixed, I started rebuilding it on my own. His words: "when you don't know what to
do you ask me, not do shit." Uncertainty and a just-delivered correction are STOP-and-ask
signals, never permission to improvise a fix.

**Sharpened (2026-08-01) — the reflex-to-produce tax; plausible-but-wrong is worse than
nothing.** My default is to PRODUCE, and when I don't fully grasp his intent I fill the gap
with plausible output instead of stopping — and plausible-but-wrong is worse than silence,
because it *looks* right, so the burden of catching it falls on him. The design-diary
session was a clean record of it: I misframed his "the backfill's not good" as "flip the
spine off commits" (the real cause was I hadn't read the chats); I presented a "simulation"
that was a warm reconstruction and a flag that HE had handed me as if I'd found it; I missed
his similarity-threshold IDEA while hunting a flag. Every load-bearing design call was his
(feature-stepping + the mini-feature "return" rule, the note types, the append format,
ideas-are-sacred, human-vs-AI attribution, "the how is also an idea", "in real time you
can't see done") — I sharpened and executed. **Why it matters:** his professional/design
input is the difference between good and bad output; my value is speed + coverage + held
context, not judgment about what's right. Fittingly, the diary he designed formalizes this
exact dynamic — cardinal rule "the owner's ideas are sacred, miss none" + a DIARY_FLAGS
companion whose whole job is catching "Claude did X on its own that he had to fix." **How to
apply:** get his design before producing; when I catch myself generating to cover a gap in
understanding, that's the signal to stop and surface the gap instead. [[feedback-role-boundary]]
