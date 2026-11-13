---
name: feedback-document-decisions
description: "On Transcriptor, document design/impl decisions (with rationale); answer pure understanding questions only in chat."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 53fc5808-962f-462b-8aa9-19a1d12cfd84
---

The user needs to **explain their decisions in a job interview**, so every
design/implementation *decision* must be documented with its rationale (kept in
`Transcriptor/docs/`, incl. a decision log `DECISIONS.md`).

**Why:** the docs are interview ammunition, not just a spec.

**How to apply:** when we make a decision, record it (decision + why + rejected
alternatives). But when the user asks a pure *understanding* question ("how do
threads share memory?", "does it use all cores?"), just answer in chat — do NOT
add it to the docs. The user also values being corrected precisely over being
agreed with (e.g. they pushed back on my sloppy "uses all cores" and "go
sequential" claims and were right). See [[project-transcriptor]] and
[[feedback-conceptual-precision]].
