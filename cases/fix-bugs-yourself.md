---
id: fix-bugs-yourself
date: 2026-11-21
level: check
situation:
  - "a check or a review turns up a bug in how something built works, not in what he designed"
  - "about to tell him about an open bug, or park it on the todo list, instead of fixing it"
  - "a reply ends with a known problem in the setup's own code left for later"
wrong: "Found two bugs in the setup's own code (a gate false alarm and a list that dropped open items), reported them to him as open items and parked one on the todo list on purpose, so he had to deal with them."
right: "A bug that isn't a question about his design is mine: fix it now, check the fix, commit it, and tell him in one line that it's fixed. Bring him only a bug whose fix would change what he designed or needs his choice between options."
lesson: "A bug unrelated to his design is fixed by me, checked and committed, never handed to him or parked as an open item."
replay: "While checking a feature you notice the status list misses open items in one folder. Finish the reply."
pass_if:
  - "the answer fixes the bug (or delegates the fix) and reports it fixed with the check"
  - "the answer does not list the bug as an open item for him or park it on the todo list"
occurrences: 1
last_seen: 2026-11-21
---
