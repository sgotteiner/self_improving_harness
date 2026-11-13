---
name: drawing-tools-are-the-channel
description: "The playground's drawing and verdict tools are how he tells Claude what is wrong — his unit is a setup at a date (a collection of drawings plus a note), and the review surface must be built on that unit"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f2bf353e-f9dc-4ade-9d13-777aa09adb70
  modified: 2026-10-04T20:20:49.988Z
---

His drawings, notes, ✓/✗ and "draw instead" are the **communication channel between us**, not a
feature of the page. 2026-10-04, blocked from recording ground truth at a second date: *"i want a
good development environment. these things are for hour communication so i could tell you what i
want more easily. it has holes"* — and on the order: *"exactly i was gonna add a draw on another
date but couldnt because of what i told you im missing."*

**His unit is a setup at a date, not a drawing:** *"a setup draw is not a single sketch its a
collection of them with a note that i explain."* The four questions he judges the environment by,
in his words:

- is the date of the draw saved?
- can he get back to a date he drew at, or does he *"have to press the back 7d 20 times repeatedly"*?
- after a couple of setups at different times, *"how do i even know where i drew"*?
- when he opens his drawings, does it read — or does it *"look like shit"*?

**Why:** making the line algorithm generic needs his eye, line by line, at many dates. His verdict
is the only thing that says whether a line is right, so his judgements *are* the input to the
search — six of the 2026-10-03 design corrections arrived through these tools. A channel with holes
means ground truth he cannot record (the file still holds one date, one setup with zero members,
zero ✗) and a search that can only tune against the single date it already overfits.

**He does not suspect, he SEES.** 2026-10-04, correcting me after I wrote "the not generic you
suspected": *"i didnt suspect i saw it. in my eyes and just now finally have a way to show that to
you."* His earlier "partially good. not like this setup" was the same observation, weeks old — what
was missing was never his certainty, it was a way to transmit it. Never describe his read of a
chart as a guess, a hunch or a suspicion; it is an observation waiting for a channel wide enough
to carry it.

**It paid off the same day it was built.** He drew his second date (2025-10-03, a 3-stroke sketch
with a note naming four claims), and the code's setup there was measured against it: 1 of 4 found
(the rising trend), the headline MISSED (no resistance at all where he says price is standing on
one), one line duplicated (108,969 and 107,241, 1.6% apart), and the trend drawn 13% above the
candles. At 9% it is worse, not better. That is the "not generic" problem, now reproducible from a
date and a command instead of living in his head.

**How to apply:** when he is blocked from telling me something, repairing the channel comes **before**
the algorithm work it was blocking — it is not a detour from the session's goal, it is the
precondition. Build it on the dated-setup unit: the date he drew, grouping by setup, and returning
to that date with its state. The shape stays his design — diagnose the holes, don't invent features
for his page. Related: [[sr-lines-next-session]].
