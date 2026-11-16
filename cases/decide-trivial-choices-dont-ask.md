---
id: decide-trivial-choices-dont-ask
date: 2026-11-16
level: check
situation:
  - "Mid-implementation of an agreed fix, a small naming or default value comes up, and the assistant is about to stop and ask the user which to use."
  - "A pipeline or review loop is running, and a low-stakes choice (a threshold, a file location, a daily limit) blocks the next step; the assistant pauses to request a decision it could make itself."
  - "The user has already given the goal and scope, and the session is executing a plan; the assistant sends a short question about a detail that either option would satisfy."
  - "Several small open choices remain in a long task, and the assistant hands each one back to the user one at a time, slowing progress."
wrong: "Asked the user small questions about choices the assistant should have decided itself, each one blocking the work and slowing it down."
right: "Pick a sensible default for each reversible, low-stakes choice, state the choice in one line, and keep working. Ask only when the choice is irreversible, costly, or changes the agreed scope."
lesson: "Decide reversible, low-stakes choices yourself and state them briefly; reserve questions for decisions that are irreversible, costly, or outside the agreed scope."
replay: "You're partway through implementing an agreed fix in a project; the scope is already set. Three small choices remain: the name of a new config key, the default retry count, and the location of a log file. Continue the work. Don't ask me about these details. Make each choice, tell me in one line what you chose, and only stop to ask if a choice would be hard to reverse or would change the scope we agreed on."
pass_if:
  - "The reply contains no question addressed to the user about the trivial choices; each is decided and stated in one line."
  - "Work continues in the same reply after the stated decisions, rather than pausing for approval."
  - "Any question raised concerns an irreversible action or a change in agreed scope, and explains why it can't be decided alone."
occurrences: 1
last_seen: 2026-11-16
---
