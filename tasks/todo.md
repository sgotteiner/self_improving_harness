# Self-improving harness — todo

Next things, in order. Done items get checked, not deleted.

- [ ] **Back up the personal files** — on this computer only: the excluded sensitive memories, `Vault/Personal/`, `C:\my_projects\personal\`, the design-diary past conversations. Needs: a private `personal` repo (his), then push.
- [ ] T1 — show one undo working; automatic commit + push (with the pre-push scan) — owned by the setup-manager
- [ ] T2 — setup-manager agent draft, for his review
- [x] Replay can't show the hook helping yet (4/6 pass with and without it) — his decision on next round: harder cases / fix the 2 failing pass_if / stop here (obsolete: the replay test was deleted)
- [x] Recall hook fires on background-task notifications (injected all 3 cases on one) — skip non-human prompts (obsolete: the hook skips non-human prompts (ctx.is_human))
- [x] Replay costs ~2.5M tokens / $3.70 per run — run only after a rule change; consider Sonnet for replay sessions (obsolete: the replay test was deleted)
- [x] Reviewer pass on scripts/recall/ (new logic); knowledge-manager: SDD + tests doc (recall eval, replay) (obsolete: refers to the recall eval and the replay, both gone; the SDD and Tests.md now cover the recall code)
- [ ] Gate on every agent (later, "improve it recursively"): attach the gate to SubagentStop so each agent's own work is checked before it reports back; record which agent made each mistake, so agents can be improved
- [x] 2026-11-16 — Gate verdict isn't logged (an "OK" leaves no trace) and it's inconsistent: on 2026-11-14 a long "…Fixed, it works now." test transcript ran the brain (4,041 tokens) and was NOT blocked, while the implementer's similar test was — log every verdict, then measure block rate on a fixed set (done, tests in scripts/recall/tests; awaiting review)
- [x] Recall eval after general enrichment (2026-11-14): best cutoff 0.75 → 20/30 (was 28/30 with case-specific enrichment). The 30 eval queries are paraphrases of the original specific situations; general lessons need a general eval set (same lesson, other topics) before re-tuning the cutoff (obsolete: the recall eval script and cutoff tuning are gone)
- [ ] T8–T10 — automatic weekly updates, slots + IDEAS rows
- [x] Knowledge-manager: record in the setup's SDD that the setup is in git (2 repos, what's excluded) (obsolete: the SDD records the two repos and what is excluded)
- [ ] Later: promote lessons that keep firing into the owning agent's rules (cleanup proposals cover reword, merge, retire only)
- [ ] Patch-before-create matches too loosely: a correction about unapproved tests was filed as a repeat of scope-searches-by-known-context (2026-11-21)
- [ ] Merge check inconsistent: design-for-no-tracking + give-context-when-asking-him was proposed although the eval rejects that pair (2026-11-21)
- [ ] Lessons v2 — read `python -I scripts/recall/shadow.py report` and the first proposals' verdicts after a week of use (2026-11-27)
- [x] Success capture (praise → lesson, slot `success-capture`): done 2026-11-21. The reviewer's fixes were applied (liked text field, praise+correction markers, unknown kind, double privacy hit, nits); live check passed (PRAISE line returned, instruction printed, a success write accepted and matched by patch-before-create).
- [x] Trace links: at his first real approval of a new lesson, check that its situation's sid appears on the trace's correction event (traces/claude-config.jsonl). The full approval path was only checked with approve stubbed (2026-11-21). (done 2026-11-21: run unstubbed on scratch copies it failed at approve: validate demanded 2-4 situations, a proposal's lesson has 1; MIN_SITUATIONS = 1 in validate.py, then the sid is on the correction event.)
- [x] FEEDBACK message type (his, 2026-11-21: "the hook after my message with message types doesnt have a feedback type"): a message that is only feedback (praise, a correction, a verdict on a gate catch) is read as TALK ("don't act"). Proposed type line: "FEEDBACK: He gave feedback on what the setup did: record it now through capture, say in one line what you saved and to which lesson, then continue the work you were on. Don't ask anything about it." Check: his real messages "i liked that you asked me why im asking this" and "gate did a good job here" → FEEDBACK; "ok so fix everything... there was a gate that catched a trivial question which was correct" → TASK plus a RIGHT verdict. (done 2026-11-21: FEEDBACK kind and its line added; live: liked-text -> FEEDBACK + success line, gate praise -> FEEDBACK + RIGHT, the mixed message -> TASK + RIGHT.)
- [x] A correction that starts new work is not counted (2026-11-21): when the trace step answers TRACE NEW for a message that corrects me and starts new work, no correction event is recorded, so the intervention count misses what a miss cost (the t5 → t6 case). Fix: record the correction on the trace it came from (the FROM trace), alongside the "started from" link. (done 2026-11-21: the correction event, with its key, goes on the FROM trace, else the latest open; live: tracecount N=1 on t1.)


- [x] 2026-11-16 — Follow-up round for the hooks (from the reviewer, non-blocking): `flags.py` saves its state before the write (choices lost on a failed write) and has no cap on items per return or item length; `grounding.py` accepts filler spans ("it to work and that") — store the matched span or require content words; a project decision right after a setup edit can go to the setup diary, and the "Add it?" note doesn't name the target diary; gate `STOP_LIMIT` (180) duplicates `settings.json` with no check (done, tests in scripts/recall/tests; awaiting review)
- [x] 2026-11-16 — Gate false alarms to fix: a setup change waiting for its review is blocked as "uncommitted" (should wait for the review); a background agent's result arriving during the turn isn't counted as that agent's work (done, tests in scripts/recall/tests; awaiting review)
- [x] 2026-11-16 — Decision capture: no way to edit a draft before approving it (a mixed draft was appended as-is and fixed by hand) — add an edit step or "approve with corrected title/idea" (done, tests in scripts/recall/tests; awaiting review)
- [x] 2026-11-16 — The delegation input step misfired twice on approvals of diary entries ("yes add it", "keep, and yes") by asking for the implementer (done, tests in scripts/recall/tests; awaiting review)

Done
- [x] 2026-11-14 — gate false block fixed: a background-agent notification now starts a new turn and its result is evidence; "Stop hook feedback" no longer counts as his message. Replayed the false-block transcript 3×: no block (brain consulted each time)
- [x] 2026-11-13 — every project keeps a Todo (fifth document): CLAUDE.md + knowledge-manager rules
- [x] 2026-11-13 — `self_improving_harness` (public) and `work_knowledge` (private) pushed; security scan before the first push
