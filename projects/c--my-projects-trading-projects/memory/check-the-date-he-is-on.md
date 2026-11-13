---
name: check-the-date-he-is-on
description: "When he reports something about the chart, check the date HE is standing on — read the VIEW line in the playground's log — and name the date behind every number"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f2bf353e-f9dc-4ade-9d13-777aa09adb70
  modified: 2026-10-05T09:47:45.955Z
---

**Everything he reports is about the date on his screen.** 2026-10-05, after a whole session of
answers computed at dates Claude chose: *"youre checking my live view right? at the time im at"* and
then *"are you fucking kidding me? you dont check what i say based on the date im at?"*

**How to know where he is:** `scripts/sr_playground.py` prints a line on every `/api/points`:

```
VIEW 2026-02-13 (bar 3102) | sizes [7.0] | band 0.0 | visits 2 | mode owner
```

Start his server with its output going to a log file and read the last `VIEW` line before answering
anything about "the lines", "the boxes", "it doesn't show". It carries the date AND the settings,
so a report can be reproduced exactly as he saw it.

**Why:** a bug report about 2026-02-13 checked at 2026-09-04 is a different chart - different
price, different move, different lines. Several "reproduced" and "could not reproduce" answers that
day were about charts he was not looking at, which wastes his time and makes the measurement a lie.

**How to apply:** read the log first, then answer. **Name the date behind every number** ("at
2026-02-13, price 68,854..."), so he can tell at a glance whether Claude is looking at his chart or
its own. When the log has no recent line, ask which date rather than picking one.
Related: [[he-gives-ideas-i-build-and-test]] · [[drawing-tools-are-the-channel]]
