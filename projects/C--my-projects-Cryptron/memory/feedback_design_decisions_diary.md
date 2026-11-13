---
name: feedback_design_decisions_diary
description: Every project keeps an append-only DESIGN_DECISIONS_DIARY.md beside its design doc — the WHY log; the design doc is the current WHAT.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: fa08eb55-0486-4585-9b07-729d132d8c49
  modified: 2026-07-28T19:09:42.980Z
---

Every project starts with a design document AND a **`DESIGN_DECISIONS_DIARY.md`** beside it (repo). The design doc = current **WHAT** (edited freely). The diary = **WHY**, a dated journal, **APPEND-ONLY** — never edit or delete, only add the next entry.

Append an entry whenever the design changes, a new problem is tackled, the architecture shifts, a lesson lands, or a new idea redirects things: date it, state the decision, give the why (the problem, the reasoning, why over the alternative, and on a change **why we left the old approach**).

**Why:** The `what` is re-derivable from code; the `why` is lost the moment it leaves the conversation, and losing it means a future session "cleans up" or reverts a hard-won decision and the system falls. The governing principle is why-first: the why is the load-bearing part of documentation, and it must survive design changes (replace the current WHAT, keep the WHY). Append-only keeps a long history trivial to maintain and makes the why permanent. Full methodology: `Vault/Meta/Documentation_Methodology.md` §0.

**How to apply:** Create the diary on day one of any new project. Keep appending; never rewrite it. The vault project note's Key decisions is the distilled highlights; the repo diary is the full log.
