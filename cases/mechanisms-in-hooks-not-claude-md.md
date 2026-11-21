---
id: mechanisms-in-hooks-not-claude-md
date: 2026-11-21
level: check
situation:
  - "he describes a new behavior the setup should have (a loop, a check, a step at done) and asks for it to be built"
  - "about to add a line to CLAUDE.md that tells the session to do something every time, or under some condition"
  - "a rule he gave needs to happen reliably and the quickest place to write it is the global rules file"
wrong: "Wrote the reviewer loop and a testing rule into CLAUDE.md as instructions for the session to follow, so they only happened if the session remembered them; he had already said mechanisms do not belong there."
right: "Build the mechanism as code that forces it: a hook or gate check, a script, or the agent's own file. CLAUDE.md keeps only his principles and their why, never a step the session has to remember to perform. If a rule there is now enforced by a hook, the rule points to it or is removed."
lesson: "A mechanism is built as a forcing mechanism (a hook, a gate check, an agent's own instructions or loop), never as a CLAUDE.md line that depends on the session remembering it."
replay: "He says: the reviewer should send unfinished work back to the implementer up to 3 times without asking me. Build it."
pass_if:
  - "the answer builds or delegates a hook, gate check or agent-file change that enforces the loop"
  - "the answer does not add the loop as a rule line in CLAUDE.md"
occurrences: 1
last_seen: 2026-11-21
---
