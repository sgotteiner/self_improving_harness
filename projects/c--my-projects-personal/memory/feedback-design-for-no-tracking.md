---
name: feedback-design-for-no-tracking
description: Never design anything that depends on him remembering to do it - the system acts or asks him where he already looks
metadata:
  node_type: memory
  type: feedback
  originSessionId: 605e2775-31ab-4460-bdfc-b9b50eccbf73
  modified: 2026-11-13T11:30:05.546Z
---

He can't track all the moving parts of the setup and his life (said 2026-11-13, about the weekly shelf-update job: "if it doesn't pull automatically and doesn't ask me I won't remember to do it. The design needs to account for that").

**Why:** too much to track; anything that waits on his memory silently never happens.
**How to apply:** every recurring task either runs by itself (safe default + rollback + a switch to turn it off) or puts the question in front of him where he already is (session start, phone notification), never "you can run X when you want". Applies to setup jobs, reminders, admin follow-ups. Related: [[feedback-token-efficiency]], [[user-life-routine]]
