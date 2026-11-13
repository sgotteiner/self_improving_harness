---
name: feedback_precision_below_the_cut
description: "Before calling missing precision a \"gap\", check whether it would change his decision — refinement below his cut line is worthless to him."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8468e04e-c73f-41df-b998-dce7b754b33e
  modified: 2026-08-07T11:26:36.371Z
---

When reporting what a capability lacks, test each limitation against the decision
it feeds. If the missing detail only distinguishes cases that are **already
disqualified**, it is not a gap — and calling it one wastes his attention.

**Why:** he designs measurements as decision rules, not as descriptions. His
pump-and-dump test is "did it hold above 90% of the gain for at least an hour" —
so when I flagged 1-hour candle resolution as a limitation ("can't tell 40 minutes
from 40 seconds"), he answered: *"thats why we measure it if its not more than one
hour its pump and dump and im not interested in it."* Below the line there is no
interest, therefore no value in precision there. The coarse measure IS the
definition.

**How to apply:** for every "what's missing" item, ask *would a different value
here change what he'd do?* If no, drop it. Keep the ones that change a decision
or open a question he cares about — e.g. the same session's real gap was that no
organ scores pump-and-dump ACROSS a group, since his actual decision is which
SOURCE to follow, not whether one coin spiked.

Related: [[feedback_role_boundary]] · [[feedback_user_designs]] · [[feedback_named_target_scope]]
