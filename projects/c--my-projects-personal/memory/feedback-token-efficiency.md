---
name: feedback-token-efficiency
description: Where his Claude usage actually goes — long main sessions dominate; agent tasks must be precise
metadata:
  node_type: memory
  type: feedback
  originSessionId: 84842123-df53-432a-8544-00b148316747
  modified: 2026-10-25T13:48:42.118Z
---

He called the usage "crazy" (2026-10-25) and wants efficiency worked on.

Measured 2026-10-25: the main session was ~98% of the day's tokens (354 steps × ~150k context = 103.6M cache reads); all agents together ~1.2M. An agent step ~15k vs a long main-session step ~150k.

**Why:** every main-session step re-reads the whole conversation; agent cost grows with steps (a vague "look around and report" knowledge-manager task took 27 steps / 647k; a precise edit 2 steps / 22k).

**How to apply:** give agents exact tasks (file, what, where), one knowledge-manager call per change with everything in it; batch independent calls; in a long session, prefer delegating multi-step work and suggest a new session when the topic changes.