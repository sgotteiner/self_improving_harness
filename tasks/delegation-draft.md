# Delegation by hooks: draft wording (waiting for the owner's approval)

Why: he does not want the delegation to depend on the main session's memory. The input hook tells the main session what
to delegate when he writes; the output gate blocks the reply when the turn skipped a delegation the core rules require.
The main session starts the agent itself, so the result comes back into the conversation.

Status: code written, switch `delegation-hook` in `slots.json` is OFF. Nothing runs until he approves this wording and
the switch is turned on. The code reads the two prompts and the instruction lines from THIS file (the fenced blocks and
the bullet list below), so what he approves here is exactly what runs. The rules themselves are not copied here:
`{rules}` is filled at run time with the section "The core: after every change, three questions" of
`CLAUDE.md` in the setup root (up to the next `## ` heading), so editing CLAUDE.md changes the behavior.

Brain: the same cheap model as the other hooks, one call per step (input: on his message; output: before the reply).

## Input step (hook.py, on his message)

Placeholders: `{rules}`, `{ctx}` (the last 4 turns), `{prompt}` (his new message).

```text
The rules of this setup (the core of its CLAUDE.md):
{rules}

Recent conversation:
{ctx}

The owner's new message: {prompt}

Does his message call for one of these delegations, by the rules above?
KNOWLEDGE-MANAGER: he says a feature or change is done, finished, or accepted as complete, and the system changed (a feature added, removed or changed).
TEST: he says something does not work, is still broken, or did not change.
IMPLEMENTER: he approves a specific change to be made now (picks an option, says go ahead, yes do it).
Anything else is NONE: a question, a request for an explanation, a discussion, planning, thanks, a color or a text change. Be strict: when unsure, NONE.
Reply 'NONE' or one line: <KNOWLEDGE-MANAGER|TEST|IMPLEMENTER> | <what changed or what he wants, one short factual sentence>.
```

Instruction lines attached to the main session's context (the fixed part; the brain's sentence is appended after "Context:"):

- KNOWLEDGE-MANAGER: Delegation (core rule 2): he says it is done. Before telling him it is done, call the knowledge-manager yourself (so its result comes back here) with what changed and his words: it updates only what the change touched: the SDD, tests if what is measured changed, the idea's row, and the project's maps per the system-map skill's update procedure.
- TEST: Delegation (core rule 1): he says it does not work. Test it from his entry point, the way he sees it, before saying it is fixed.
- IMPLEMENTER: Delegation: he approved a change. Delegate it to the implementer (start it yourself) with Why, task, paths and the test command.

## Output step (gate.py, before the reply)

Placeholders: `{rules}`, `{human}` (his latest message), `{tools}` (the turn's tool calls: files edited with the change, agents called, commands run), `{text}` (the final message), `{facts}` (counted by the code from the transcript, not remembered: the order of implementer and tester agent calls since his latest message with the number of completed implementer-to-tester rounds, and the setup files edited since then, not counting pending drafts or the to-do list, with whether the setup-manager was called).

```text
The rules of this setup (the core of its CLAUDE.md):
{rules}

His latest message: {human}

The assistant's turn. Tool calls (files edited with the change, agents called, commands run):
{tools}

Final message:
{text}

Facts counted from the transcript:
{facts}

Apply the three questions to this turn, from why he asked:
TESTER: logic or code was changed and its purpose is measurable (behavior, a number, a strategy), and no test, measurement or tester agent ran this turn.
REVIEWER: a new feature or a logic change was made and no reviewer agent was called this turn.
KNOWLEDGE-MANAGER: he said the feature or change is done, the system changed, and no knowledge-manager agent was called this turn.
LOOP: the core's loop (question 1: the measured purpose fell short, implementer then tester, at most 2 rounds, then back to him with the evidence). Read the results of the tester or test in this turn. (a) A test or tester result says the measured purpose fell short, the facts show fewer than 2 completed rounds, and no implementer round was started after that result: reason "start round N: implementer with the evidence, then the tester" (N = completed rounds + 1). (b) The facts show 2 completed rounds and the last result still fell short, and this turn started a third implementer round or ended without giving him the evidence: reason "2 rounds done: stop and bring him the evidence". A result that met the purpose, or no result: not LOOP.
SETUP-MANAGER: the facts list setup files edited and say the setup-manager was not called. The setup-manager owns git, hooks, slots, the shelf, vetting tools, cases and replay; every change is a commit with its why, with a scan for secrets and personal data before any push.
A color, a text, a style, a typo, a rename with no behavior change; a question or explanation; no file edited and he did not say it is done: OK. Be strict: when unsure, OK.
If several apply, report the first in this order: LOOP, TESTER, REVIEWER, KNOWLEDGE-MANAGER, SETUP-MANAGER.
Reply 'OK' or 'BLOCK <LOOP|TESTER|REVIEWER|KNOWLEDGE-MANAGER|SETUP-MANAGER> | <one short sentence: what was changed and what is missing; for LOOP the reason given above>'.
```

Block reasons (the fixed lead; the brain's sentence follows):

- TESTER: Delegation gate (core rule 1): call the tester or run the test of the purpose before you finish.
- REVIEWER: Delegation gate (core rule 3): call the reviewer on this change before you finish.
- KNOWLEDGE-MANAGER: Delegation gate (core rule 2): call the knowledge-manager with what changed and his words before you finish.
- LOOP: Delegation gate (core rule 1, the loop):
- SETUP-MANAGER: Delegation gate: call the setup-manager with what changed and why: it commits with the why, scans before any push, and runs the replay if cases changed.

The gate never blocks twice in a row (`stop_hook_active`), and fails open: any error means no block.

## Questions for him

1. Is the wording of the three instruction lines and the five block reasons right?
2. Should the input step also fire on "yes" / "go" right after the assistant proposed options? (As written: yes, as IMPLEMENTER.)
3. Turn the switch on: set `"delegation-hook": {"enabled": true}` in `slots.json`.
