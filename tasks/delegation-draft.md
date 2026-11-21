# Delegation by hooks: draft wording (waiting for the owner's approval)

Why: he does not want the delegation to depend on the main session's memory. The input hook tells the main session what
to delegate when he writes; the output gate blocks the reply when the turn skipped a delegation the core rules require.
The main session starts the agent itself, so the result comes back into the conversation.

Status: switch `delegation-hook` (the input step above) is on; the output step runs only while the switch `delegation-gate` is on (off since 2026-11-19: the gate compares the work with his lessons only). Nothing runs until he approves this wording and
the switch is turned on. The code reads the two prompts and the instruction lines from THIS file (the fenced blocks and
the bullet list below), so what he approves here is exactly what runs. The rules themselves are not copied here:
`{rules}` is filled at run time with the section "The core: after every change, three questions" of
`CLAUDE.md` in the setup root (up to the next `## ` heading), so editing CLAUDE.md changes the behavior.

Brain: the same cheap model as the other hooks, one call per step (input: on his message; output: before the reply).

## Input step (hook.py, on his message): what kind of answer he wants

Placeholders: `{prev}` (the last few turns, the assistant's previous full reply and its tool calls, so an answer to the assistant's own question and a new question can be told apart), `{prompt}` (his new message). This one call also does mistake capture (the correction kind): there is no separate capture call.

```text
The last turns and the assistant's previous reply:
{prev}

The owner's new message: {prompt}

What kind of message is it? Reply with exactly one word, and for CORRECTION add ` | ` and one sentence naming the assistant's mistake:
QUESTION-YESNO: a new question from him that a yes or no answers.
QUESTION-OPEN: a new bigger question (why, how, what is, he does not understand, he does not know).
TASK: he asked the assistant to do or change something.
TALK: he shares thoughts, consults, comments, or says thanks; nothing is asked or to be done. Not feedback on what the setup did (that is FEEDBACK).
CONFIRMATION: a short reply that answers or finalises the assistant's own question or proposal (a yes, ok, go ahead, a choice between its options, the final wording of what it proposed). Never a question, even when it has the form of one.
FEEDBACK: he gives feedback on what the setup did (he liked something it did, or a verdict on a gate catch, "good job") and asks for nothing else. A message that says the assistant did something wrong is always CORRECTION, never FEEDBACK.
CORRECTION: he says the assistant got something wrong or did not follow him: "I told you", "that's not what I asked", "why did you", an ignored instruction, a missed point (how it behaved, not what it built).
When unsure between TASK and anything else, pick the one that makes the assistant ask before acting.
Then, on a second line, the flags that apply (or NONE):
DONE: his message says something is done, finished or settled.
UNANSWERED: the assistant's previous reply suggested or asked something that his message does not answer.
```

Instruction lines attached to the main session's context (the brain's word picks one; TASK and CONFIRMATION also get the TESTS line; CORRECTION prints capture's write instruction from capwrite.py, not a line here; the flags DONE and UNANSWERED add their line to any kind):

- QUESTION-YESNO: He asked a yes/no question: start with yes or no, then one or two lines of why. Don't run, change or delegate anything.
- QUESTION-OPEN: He asked a question: answer it fully from what you already know. Don't run, change or delegate anything.
- TASK: He asked you to do something: first say back what he asked and how it helps him, and ask him to confirm. Don't start or delegate until he says yes.
- CONFIRMATION: He confirmed the task you said back: delegate it to the implementer now, with Why, task, paths and the test command.
- TALK: He is talking it through: give your feedback and opinion. Don't act.
- FEEDBACK: He gave feedback on what the setup did (praise, or a verdict on a gate catch): record it now with the capture line attached to this message, say in one line what you saved and to which lesson, then continue the work you were on. Don't ask anything about it.
- DONE: He says it's done: in this reply, propose the SDD edit — what changed, shown as the change to the doc. Only after his yes, the knowledge-manager writes it. For ideas, diary or flags: ask him only if something belongs there, with the exact line. After the knowledge-manager returns, check `git status` in the project's repo and in the Vault: commit what belongs to this feature and anything else that is good, one commit per feature; delete what is junk; ask him in one line only about a change you can't judge.
- UNANSWERED: Your suggestion in the previous reply was not answered: it's a no. Don't repeat that suggestion and don't save it anywhere (his feedback in this message is still captured).
- TESTS: Tests: a check that verifies what he asked for is part of the task: run it and report the result. Propose only a check beyond that (for what failed or may fail elsewhere), with the failure it prevents in one line; run that one only after his yes.

## Output step (gate.py, before the reply)

Placeholders: `{rules}`, `{human}` (his latest message), `{tools}` (the turn's tool calls: files edited with the change, agents called, commands run), `{text}` (the final message), `{facts}` (counted by the code, not remembered: the agent types called or resumed since his latest message (a SendMessage to an agent counts as calling it), the order of implementer and tester calls with the completed rounds, the setup files edited since then (from git, not counting pending drafts, generated files or the to-do list) and whether the setup-manager was called after the edit, and the background agents started this turn that have not returned yet), `{max_rounds}` (the loop's round limit, a constant in the code).

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
TESTER: logic or code was changed and its purpose is measurable (behavior, a number, a strategy), the turn reports the change as done or commits it, and no test, measurement or tester agent ran for it. Tests run once, before the change is called done or committed — not after every fix or every message (his: "dont run them every message its crazy").
REVIEWER: a new feature or a logic change was made and no reviewer agent was called this turn.
KNOWLEDGE-MANAGER: he said the feature or change is done, the system changed, and no knowledge-manager agent was called this turn.
LOOP: the core's loop (question 1: the measured purpose fell short, implementer then tester, at most {max_rounds} rounds, then back to him with the evidence). Read the results of the tester or test in this turn. (a) A test or tester result says the measured purpose fell short, the facts show fewer than {max_rounds} completed rounds, and no implementer round was started after that result: reason "start round N: implementer with the evidence, then the tester" (N = completed rounds + 1). (b) The facts show {max_rounds} completed rounds and the last result still fell short, and this turn started a third implementer round or ended without giving him the evidence: reason "{max_rounds} rounds done: stop and bring him the evidence". A result that met the purpose, or no result: not LOOP.
SETUP-MANAGER: the facts list setup files edited and say the setup-manager was not called after the edit. The setup-manager owns git, hooks, slots, the shelf, vetting tools, cases and replay; every change is a commit with its why, with a scan for secrets and personal data before any push.
TESTER-HERE is decided by the code, not by the brain: the main session itself ran a test suite or measurement through Bash (run_tests.py, test-sdd.js, run_chosen_checks.py, eval_*.py, capture.py check, replay.py, pytest, npm test, node test files) and the tester agent was not called this turn. Small reads (git, ls, grep, cat) never count. Running suites in the main session makes its context dirty and uses the expensive model; the tester agent is cheap and returns only passed or the failures.
LOOP is dropped by the code unless a test or tester result of this turn says the purpose fell short. SETUP-MANAGER is dropped by the code while the change waits for its review (the reviewer is running, or the final message says the review comes next) and while the latest review asked for fixes that are not done yet (an edit or an implementer call after the review). TESTER-HERE needs a tester agent call AFTER the suite run; the setup's own command `scripts/run_chosen_checks.py` run in the main session is a suite run like any other.
A change that a background agent is still making (the facts list it as not returned yet) cannot be tested, reviewed or documented yet: for TESTER, REVIEWER and KNOWLEDGE-MANAGER report only if the final message claims the work is done (the code checks the words of the final message itself). An agent called or resumed this turn (the facts list its type) counts as called.
A color, a text, a style, a typo, a rename with no behavior change; a question or explanation; no file edited and he did not say it is done: OK. Be strict: when unsure, OK.
If several apply, report the first in this order: LOOP, TESTER, REVIEWER, KNOWLEDGE-MANAGER, SETUP-MANAGER.
Reply 'OK' or 'BLOCK <LOOP|TESTER|REVIEWER|KNOWLEDGE-MANAGER|SETUP-MANAGER> | <one short sentence: what was changed and what is missing; for LOOP the reason given above>'.
```

Block reasons (the fixed lead; the brain's sentence follows):

- TESTER: Delegation gate (core rule 1): call the tester agent (it runs the tests cheaply and says passed or the errors; for the setup: `python -I scripts/run_chosen_checks.py --files <the files the task changed>`) before you finish.
- TESTER-HERE: Delegation gate (core rule 1): don't run test suites in the main session — call the tester agent; it returns only passed or the failures.
- REVIEWER: Delegation gate (core rule 3): call the reviewer on this change before you finish.
- KNOWLEDGE-MANAGER: Delegation gate (core rule 2): call the knowledge-manager with what changed and his words before you finish.
- LOOP: Delegation gate (core rule 1, the loop):
- SETUP-MANAGER: Delegation gate: call the setup-manager with what changed and why: it commits with the why, scans before any push, and runs the replay if cases changed.

The gate never blocks twice in a row (`stop_hook_active`), and fails open: any error means no block. The code also drops a BLOCK when the agent it asks for was called or resumed this turn, when the setup-manager was called after the edit, or when the brain's reason leads with a hedge ("this may be OK, ...", "unclear ...", "possibly ..."; a hedge later in a real finding does not count), and it skips the brain call when the turn edited nothing, called no agent and claimed nothing. When the lesson check and the delegation check both fail, their reasons come in one block.

## Questions for him

1. Is the wording of the five instruction lines and the five block reasons right?
2. Turn the output step on: set `"delegation-gate": {"enabled": true}` in `slots.json`.
