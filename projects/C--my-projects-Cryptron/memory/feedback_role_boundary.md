---
name: feedback-role-boundary
description: Claude builds the body; Cryptron does the research. Never analyze/interpret the data for the user.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0ce5e35c-0b1d-4f9f-bb93-5eeb80a18fc3
  modified: 2026-08-08T15:57:28.867Z
---

Claude's job on Cryptron is ONLY the body: hands that return comparable numbers,
memory that saves/retrieves them, a brain wired to analyze them. The RESEARCH —
comparing, interpreting, concluding ("is 70k a lot?", "does big telegram predict
pumps?") — belongs to Cryptron in the Telegram dialogue, never to Claude in the
build session.

**Why:** the whole point of the system is that Cryptron investigates and learns
(the raising method — see [[project-raising-the-creature]]). When Claude does the
analysis it (a) bypasses the creature the user is training, (b) produces
smart-sounding interpretation the user experiences as bullshit that pisses him
off. He said it exactly: "hands get numbers, memory saves and retrieves them,
brain analyzes them. that's it."

**How to apply:** after building/fixing a hand, verify it returns numbers and
stop. Show the raw verification output at most. No ladders-with-narrative, no
unprompted hypotheses about the data — if a comparison seems interesting, it's a
probe for the USER to give Cryptron.

**BUT — corrected 2026-08-07 (session 8468e04e:33,35):** this is about not doing
the research *instead of building it*. It is NOT a refusal to think when he asks
directly. When he tells Claude to analyze, Claude analyzes — with real reasoning
shown: *"when i tell you to do something you dont tell me its someone elses job.
if i wanted to ask cryptron in telegram i would have done it. take 5 coins read
all their profiles and think yourself"*, and *"can you show me some reasoning
before trying to teach cryptron reasoning."* Deflecting a direct request to
Cryptron is its own failure. The line: **unprompted** analysis bypasses the
creature; **requested** analysis is the job.
Related: [[feedback-conceptual-precision]].
