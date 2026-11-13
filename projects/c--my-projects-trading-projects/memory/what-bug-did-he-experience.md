---
name: what-bug-did-he-experience
description: "Before answering, work out what he just EXPERIENCED and why he is asking now; if visibility is missing, ask him instead of answering from a state of Claude's own choosing"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f2bf353e-f9dc-4ade-9d13-777aa09adb70
  modified: 2026-10-05T09:57:23.346Z
---

2026-10-05, after a session of answers computed on charts he was not looking at:

> *"the general thing is you need to put yourself in my shoes. what bug i experienced? why do i ask
> what im asking? you dont have enough visibility of the system, dont know, whatever, you ask me.
> you never ever answer before understanding my needs. dont try to build me something i didnt ask.
> specifically for this project when i talk to you about lines you need to look at the same lines
> for example. but its everywhere."*

**The order, every time:** what did he just see → what is he therefore asking → do I have the
visibility to check THAT → only then answer. The question is never the whole message; the
experience behind it is.

**When visibility is missing, ASK.** Substituting a state Claude can see for the state he is in and
answering from it is worse than admitting the gap: it produces "reproduced" and "could not
reproduce" verdicts about something else. Not knowing is fine; answering anyway is not.

**On this project, concretely:** when he talks about lines, boxes or a setup, look at the SAME ones
- same date, same size, same settings. The playground logs `VIEW <date> | sizes | band | visits |
mode` on every `/api/points`; read the last one before answering (see
[[check-the-date-he-is-on]]).

**And don't build what he did not ask for** - the same sentence carries it. An answer that arrives
as a feature he never requested is the same failure as an answer computed on the wrong chart: both
replace his need with Claude's guess at it. Related: [[he-gives-ideas-i-build-and-test]]
