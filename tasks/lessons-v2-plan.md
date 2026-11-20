# Implementation Plan: Lessons v2

Status: draft for his approval (2026-11-20). Idea row: Vault IDEAS.md "Lessons v2". Other open plan: tasks/plan.md (untouched).

## Overview
Lessons become one store — the lesson (the current general principle) and its situations (the real cases behind it, append-only) —
with everything else derived from it: the all-lessons text the gate reads, the stats, the per-lesson history pages, embeddings.
Around the store: new lessons are checked against existing ones first (patch before create), each firing is traced to its closest
situation, cleanup is proposed when the lessons grow too big or a lesson stops earning its place, lessons are learned from the work
as well as from his corrections, and "select" delivery runs in shadow next to "all" so the two can be compared on real data.
Everything that changes the knowledge reaches him as one proposal line: yes, or ignore (= no).

## His words that set the design
- "we could save lessons from complaints and successes. its also good to have one thing (lessons)"
- "we need to design that in a way we could switch between them since we are still testing it"
- "when its truly separated i can also then do whatever i want to it like add embeddings or the stats"
- "restricting merges and edits for a specific situation that i will never be in again can also hurt the self improvement"
- "when you use a lesson you also trace back to which situation it was most similar"
- "make it easy for me to just approve or ignore" / "just make sure its well structured" / "nobody likes duplicates and generic lessons are the idea"

## What exists today (reused, not replaced)
- `cases/<id>.md` — one file per lesson: lesson, right, wrong, hand-written `situation:` lines, occurrences, last_seen
- `scripts/recall/history.db` — raw repeats (local, never pushed); `cases/history/<id>.md` — cleaned repeats, generated (52 blocks over 9 lessons)
- `alllessons.py` — builds the all-lessons text (id, lesson, right) for the gate; `LESSONS_MAX` = 12000 chars (logs only)
- `cases/stats.json` — right / wrong / missed / ignored per lesson, from his verdicts (`capverdict.py`)
- `cases/_pending/` — draft lessons waiting for his yes; `slots.json` switches; `retrieve.py`/`embed.py`/`graph.py` (the select path, off)

## Architecture decisions
1. **Store = text files, git-diffable.** Lessons stay `cases/<id>.md`. Situations move to one `cases/situations.jsonl`, one line each:
   `{sid, lesson_id, date, source: correction|gate|work|seed, situation, did, outcome, status: active|retired, hits, last_hit}`.
   Seeded from the cleaned history blocks and the hand-written `situation:` lines. history.db stays the raw local log. No Parquet, no DB.
2. **Derived = rebuildable, never edited by hand:** `cases/history/<id>.md`, the all-lessons text, a combined `cases/LESSONS.md` (the
   "forever updating CLAUDE.md" he can read), stats views. One build command regenerates all of them.
3. **One proposal queue + one proposal line.** `cases/_pending/` becomes the queue for every kind (new lesson, edit, merge, retire
   situation, retire lesson, revert). At most one line a day at the end of a reply; his yes (read by the existing message-step call,
   as the verdicts are) applies it; no answer = no, dropped. Nothing is deleted: retired lessons go to `cases/_archive/` with their stats.
4. **Delivery switch stays `recall-all-lessons`**, now reading the store; "select" reads the same store (situations as search texts).
5. **Edits are measured after, not restricted before:** an edit is checked once against the kind of mistake of its active situations
   (one cheap call); after it is applied, a rise in `missed` for that lesson produces a revert proposal.

## Task list

### Phase 1 — Foundation: the store
- [ ] **Task 1: Situations store, seeded.** `cases/situations.jsonl` from the 52 cleaned blocks + hand-written situation lines;
  capture's write appends a line (and still records history.db). `cases/history/<id>.md` is generated from the jsonl.
  - Acceptance: every cleaned block and situation line has exactly one jsonl line with its lesson id; regenerated history pages
    have the same blocks as today's; a new capture write adds one line.
  - Files: new `scripts/recall/situations.py`; `capwrite.py`, `history.py`; tests. Size: M.
- [ ] **Task 2: Derived views from the store.** One build command; `alllessons.py` reads through it; `cases/LESSONS.md` generated.
  - Acceptance: the gate's all-lessons text is byte-identical before and after on today's lessons; LESSONS.md lists all lessons.
  - Files: `alllessons.py`, `situations.py`, `index.py`; tests. Size: S.

### Checkpoint A — gate unchanged on the new store; his look at LESSONS.md

### Phase 2 — Proposals and no duplicates
- [ ] **Task 3: Proposal queue and line.** Queue kinds, one line a day, his yes applied, no answer dropped, archive instead of delete.
  - Acceptance: a queued proposal shows once; "yes" applies it; any other reply drops it; two queued → one shown per day.
  - Files: new `scripts/recall/proposals.py`; `delegate.py` (yes read in the existing call), `gate.py` or `hook.py` (the line); tests. Size: M.
- [ ] **Task 4: Patch before create.** A new lesson (from capture) is compared with all lessons in one cheap call: same kind of mistake
  as an existing one → the proposal is a wording edit of that lesson + its situation attached; otherwise a new-lesson proposal.
  - Acceptance (check): today's declined "word it so it can't be misread" and a paraphrase of `report-without-testing` → SAME as the right
    lesson; a truly new mistake → NEW.
  - Files: `capwrite.py`, `proposals.py`; tests. Size: S.

### Phase 3 — Tracing and cleanup
- [ ] **Task 5: Situation tracing.** When a lesson fires (his RIGHT verdict, or a missed correction), one small call with that lesson's
  situations picks the closest → `hits`, `last_hit`; none close → flagged as a new kind (goes into Task 4's decision).
  - Acceptance: a firing on a known situation raises that situation's hits by one; an unlike case is flagged new.
  - Files: `capverdict.py`, `capwrite.py`, `situations.py`; tests. Size: S.
- [ ] **Task 6: Cleanup proposals.** Started when the lessons text crosses the size limit, and weekly. Rules from the stats and hits:
  often wrong → reword; often missed → the gate misreads it, reword; never named / situations never hit for N weeks → retire;
  overlapping lessons → merge. An edit is checked against its active situations before it is proposed; after it is applied, `missed`
  rising → revert proposal.
  - Acceptance: on a fixture store each rule produces its proposal and nothing else; a merge keeps every active situation linked.
  - Files: new `scripts/recall/cleanup.py`; `proposals.py`; tests. Size: M.

### Checkpoint B — review; proposals live for a week before Phase 4

### Phase 4 — Learning and comparing
- [ ] **Task 7: Shadow select.** On each gate call, log which lessons "select" (embedding over situations) would have sent; a report
  compares it with what "all" named.
  - Acceptance: every gate call writes one shadow line; the report gives, per lesson named by "all", whether select would have had it.
  - Files: `gate.py`, `retrieve.py`, `gate_report.py`; tests. Size: S.
- [ ] **Task 8: Learning from the work.** When he says done (the message step's DONE flag), a background review of that stretch of work
  drafts at most one lesson (source work) → Task 4 → proposal.
  - Acceptance: a fixture transcript with a struggle and its fix gives one draft; a plain transcript gives none.
  - Files: new `scripts/recall/workreview.py`; `hook.py`; tests. Size: M.

### Checkpoint C — complete: SDD updated, review, his verdicts on the first proposals

### Phase 5 — feature traces, part of learning from the work (his words 2026-11-20: "i thought it was part of the learning from work. i want that")
- [ ] **Task 9: Trace store and events.** `traces/<project>.jsonl` (local to the setup repo, tracked): one trace per feature {tid, project,
  title, why (the problem that led to it, quoted from the turns before the ask), opened, events[], closed}. The message step's existing
  call adds one flag line `TRACE <tid> | NEW <title> | <why quote> | NONE` (no second call). Events added by code, no model call:
  his correction (message type), an agent return (reviewer findings / implementer / tester result, first line), a commit (hash +
  subject from the turn's tool output), DONE closes it.
  - Acceptance: a task message opens a trace with its why; a follow-up on it attaches, not a new one; a correction, a reviewer return
    and a commit each add one event; DONE closes it.
- [ ] **Task 10: Done → learning and record.** At DONE the work review reads the trace (its events + the stretch) instead of the last
  turns only; the main session is told once to call the knowledge-manager with the trace for the Ideas row (problem, tried, result,
  next) and the SDD if the system changed. Hooks never edit the vault.
  - Acceptance: a closed trace gives the work review its events; the session gets exactly one "record this trace" instruction.
- Check: unit tests (mocked call); one live run of the TRACE flag on today's real messages: "i like the tracing to see which lessons are
  good" → NEW with the why from the graph-memory turns before it; "i thought the stats were by my approval ..." → the same trace.

## Checks (the measured purpose; proposed here, run only with his yes on this plan)
- Phase 1: the gate's input is unchanged — byte-identical all-lessons text, and history pages unchanged. Prevents the migration
  silently changing what the gate judges by.
- Task 4: duplicates are caught — the two known cases come out SAME, a new one NEW. Prevents the lesson list splitting.
- Over time (no test, his stats): `missed` and `wrong` per lesson after edits; shadow-select hit rate.
- Each task: `python -I scripts/run_chosen_checks.py --files <changed files>` (the tester runs it).

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| Migration changes what the gate sees | High | Task 2's byte-identical check before anything else |
| Proposal noise | Med | one line a day; no answer = no; work lessons only through Task 4 |
| Too little data for retirement rules | Med | stats started today; Task 6's thresholds are named constants, his to set |
| A cheap-model call per firing adds cost | Low | only on firings (a few a day), only that lesson's situations |

## His answers (2026-11-20) — plan approved
1. Order: keep.
2. Size limit: smaller, "start with hermes like at least for the total lessons size" → 2200 characters of all-lessons text
   (today 4047 over 11 lessons, so the first cleanup proposals start as soon as Task 6 is live).
3. Retire after 4 weeks without a hit: ok.
4. Learning from the work: both — at his "done" and every 10 turns since the last learning review ("lets say n is 10 turns from the last learn").
