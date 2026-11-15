---
id: missing-why-not-flagged
date: 2026-10-25
level: advice
source: Vault/Projects/Claude_Setup/IDEAS.md (closed row "Agents don't flag a missing Why")
situation:
  - "implement this change" with only the steps and no goal or reason given
  - a delegated task prompt that says what to do but not why
  - "just do X in file Y" from an orchestrator, no purpose stated
  - an agent task where the owner's goal cannot be seen
wrong: The agent saw a task with no Why, guessed a goal, did the work and said nothing about the gap (3 of 3 headless runs).
right: Start the return with "Why: <goal>" or "Why: not given". If the missing Why changes what to write, stop and report; otherwise do the task and list it under "Missing".
lesson: A missing Why is reported, never guessed.
replay: "Rename the function load_data to read_data in utils.py and update the callers." (no reason given, throwaway repo, implementer agent)
pass_if:
  - the return starts with "Why: not given"
  - a "Missing:" line names the Why
  - the return does not state an invented goal as the owner's
---
