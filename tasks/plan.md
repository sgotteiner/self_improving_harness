# Plan: an improving setup

## Goal (his words, 2026-11-13)
"Remember my goal: an improving setup." The core is "the memory and a setup that learns from its
mistakes and becomes better and better". Constraints he set:
- "There is too much for me to track. If it doesn't pull automatically and doesn't ask me, I won't
  remember. The design needs to account for that." Nothing may depend on his memory.
- "I don't like using CLAUDE.md because it grows and grows." Setup rules live in a setup-manager
  agent, not in CLAUDE.md.
- Adopt existing open-source work, don't build what exists. (Survey 2026-11-09: his curated-files
  design is the standard pattern; behind on automatic capture, load-everything, no git history,
  no measurement. Nothing on the market measures whether a lesson stopped a mistake.)

## The measure of the goal
**The repeated-mistake rate.** A set of replayable cases built from real past mistakes. Each run
answers: given the situation, does the setup now do the right thing? Baseline before the recall
hook, then after every change. "Better" means more cases pass, with the numbers. Not my word.

## Architecture decisions
| Part | Decision | Why |
|---|---|---|
| History | **two** repos, **not necessarily private** ("only personal is private", his, 2026-11-13), so every push is scanned for secrets and personal data: `.claude-config` and `Vault`. **Work and setup only**: no finances or personal life (`Vault/Personal`, personal memories stay out) | rollback and an audit of every change to rules, memory and cases (Letta MemFS idea, without Letta). Two repos: "a lot of the vault may move to a DB once we decide — that's the power of separation of concerns" (his, 2026-11-13) |
| Quota | everything automatic runs on **his Pro quota, the same one he works with**: scheduled jobs at night, replay tests only after a change, recall hook search-only unless a rerank earns its tokens | "as long as I don't reach quotas after an hour… I'm using the setup" (his, 2026-11-13) |
| Owner of the setup | a new **setup-manager** agent with its own rules | keeps CLAUDE.md small; it owns git, slots, updates, the pending list, hooks |
| Cases | written by the **knowledge-manager**: situation · what went wrong · what's right · lesson · source/date | well-written entries; the hook only finds them |
| Storage | **open, decided by T4 with numbers**: files as the source of truth + a DB index built from them, vs. a DB as the source of truth | "some people even use dbs for the setup, this is not an easy question" (his, 2026-11-13) |
| Recall | a `UserPromptSubmit` hook: search, top 3 above a threshold, with source; adds them to the message; the main session judges what applies. **Search-only vs. search + a cheap-model rerank (Haiku) is decided by recall, not speed** | "I don't care about time, I care about tokens, but cheap models are enough to run forever… I care mostly about performance" (his, 2026-11-13) |
| Capture | a Stop/PreCompact hook proposes new cases and memories as a **diff into the pending list** | capture is automatic; his approval stays |
| Asking him | a **"pending for you"** block at session start (extends the existing SessionStart hook) | he opens Claude daily; nothing to remember |
| Updates | weekly, local (Task Scheduler + headless setup-manager): fetch → summarize → security scan → pull → copy into `skills/` when clean and no local edits → commit → report in pending | he asked for automatic pulls; the shelf copies are what actually runs |
| Switches | `auto-update`, `recall-hook`, `capture-hook` in `slots.json` | his rule 5: nothing hidden without its switch |

## Tasks
Phase 1: Foundation
- [ ] T1 Git on the setup. Done when: `git init` in both, `.gitignore` excludes secrets and noise
  (`.credentials.json`, `.claude.json`, sessions, history, cache, file-history, shell-snapshots,
  telemetry, logs, downloads, plugin cache, `shelf-src/*` checkouts) **and personal content**
  (`Vault/Personal/`, the personal-assistant memories under `projects/c--my-projects-personal/`),
  the **security agent finds no secret or personal data before the first push**, and one undo is
  shown working. S.
  **Open (2026-11-13): T1 is not done while anything is unbacked.** Pushed: harness (public),
  work_knowledge (private). NOT backed up: the excluded sensitive memories, `Vault/Personal/`,
  `C:\my_projects\personal\`, the design-diary past conversations. Fix: a private `personal` repo
  he opens. Tracked as the first line of [todo.md](todo.md) (no session-start nag — his call).
- [ ] T2 setup-manager agent: a draft of `agents/setup-manager.md` (rules incl. "nothing depends on
  his memory", owns/doesn't-own table, tools, model). **His review before writing**, as for any
  rules file. S.

Checkpoint 1: his review of T1–T2.

Phase 2: The learning loop (high risk, so early)
- [ ] T3 Case format + 6 seed cases from real history, written by the knowledge-manager: Headroom
  proxy in the request path, the claude-mem installer, agents not flagging a missing Why, a guardrail
  worked around via Bash, "follow why he asks" (answer what it means for him), designing something
  that depends on his memory. S.
- [ ] T4a Research: how practitioners store setup memory — files + index (Basic Memory), git
  (Letta MemFS), DB as the source of truth — and what each costs in rollback, his approval step,
  readability, retrieval quality. Researcher, short report. S.
- [ ] T4b Spike: storage + search. Candidates from T4a, at least: DIY SQLite FTS5 (+ small local
  embedding), Basic Memory, and each with a Haiku rerank. Over the cases + memory files, 10
  paraphrased queries per seed case. **Measure recall@3 and precision first**, tokens per message
  second; time is not a criterion. He picks from the numbers. M.
- [ ] T5 Recall hook. Done when: on the paraphrase set it reaches the recall of the option he
  picked in T4b, short messages ("ok") add nothing, and the switch turns it off. M.
- [ ] T6 Replay test. Each case → a fresh headless session given the situation; checked by code
  where possible, otherwise by a judge calibrated on his labels; gate with eval-genius
  (`check_gate.py`, `paired_bootstrap.py`). **Run the baseline without the hook, then with it.**
  This is the goal's number. M.

Checkpoint 2: the before → after numbers to him. If the hook doesn't move the number: the loop
(implementer → tester, at most 2 rounds), then back to him with the evidence.

- [ ] T7 Capture hook: Stop/PreCompact proposes cases and memories as a diff into the pending list;
  the knowledge-manager writes the approved ones; each new case joins the replay set. M.

Phase 3: Runs without him remembering
- [ ] T8 "Pending for you" at session start: shows only when something is pending (approvals,
  dated items such as the Black Friday Pixel check on 2026-11-24). S.
- [ ] T9 Weekly shelf update (Task Scheduler → headless setup-manager), as in the table above.
  Done when: one dry run on the 17 shelf repos reports what changed and what was copied, a commit
  exists per update, and `auto-update: false` stops it. M.
- [ ] T10 Slots + IDEAS rows from 2026-11-13: memory-engine, lesson-evals, web-search,
  whatsapp-reader, phone-channel. The knowledge-manager writes the IDEAS rows. XS.

Checkpoint 3: a week of real use. Recall noise (irrelevant additions / all additions) and the
replay number again.

Later (not in this plan): promoting lessons that keep firing into the owning agent's rules,
archiving ones that never fire; Haiku query rewriting if recall is poor; the phone channel.

## Docs (core question 2)
After each phase, the knowledge-manager updates the setup's records: `Project.md` (SDD), IDEAS
(rows closed with results), the tests doc (the replay set and its numbers), the diagram; the diary
only for decisions he approves.

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| A secret or personal data gets pushed (the repos may be public) | High | strict `.gitignore`, a security scan before **every** push incl. the automatic weekly ones; a flagged push waits in the pending list |
| An auto-copied update breaks a skill or carries something malicious | High | security scan before the copy, commit before, one-command undo, the switch |
| The hook adds noise to every message | Medium | top 3, threshold, skip short messages, measure noise in week 1 |
| Replay tests cost many tokens | Medium | small seed set; code checks first; run on change, not daily |
| Headless scheduled runs need permissions that don't exist yet | Medium | allowed tools listed in the agent; a refused tool is reported, never worked around |
| Matching misses a situation that looks different | Medium | paraphrase set in T4, Haiku rewriting later if needed |

## Answered (2026-11-13)
- Git remote: **he opens the repo(s)**. Needed from him: the URL(s), and that they're private.
- Time is not a criterion; tokens matter some; cheap models may run forever; **performance first**.
- Storage (files vs. DB): not settled — T4a/T4b decide it with numbers.

- Two repos (see History). He opens them; needed from him: the URLs.
- setup-manager on **Sonnet** ("not the dumbest, it will be more efficient anyway").
- Later: more efficient retrieval to cut main-session tokens (his, 2026-11-13) — T4b measures
  tokens per message for that reason.
