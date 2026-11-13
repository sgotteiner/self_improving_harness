# Self-improving harness — todo

Next things, in order. Done items get checked, not deleted. The plan: [plan.md](plan.md).

- [ ] **Back up the personal files** — on this computer only: the excluded sensitive memories, `Vault/Personal/`, `C:\my_projects\personal\`, the design-diary past conversations. Needs: a private `personal` repo (his), then push.
- [ ] T1 — show one undo working; automatic commit + push (with the pre-push scan) — owned by the setup-manager
- [ ] T2 — setup-manager agent draft, for his review
- [ ] Replay can't show the hook helping yet (4/6 pass with and without it) — his decision on next round: harder cases / fix the 2 failing pass_if / stop here
- [ ] Recall hook fires on background-task notifications (injected all 3 cases on one) — skip non-human prompts
- [ ] Replay costs ~2.5M tokens / $3.70 per run — run only after a rule change; consider Sonnet for replay sessions
- [ ] Reviewer pass on scripts/recall/ (new logic); knowledge-manager: SDD + tests doc (recall eval, replay)
- [ ] Gate on every agent (later, "improve it recursively"): attach the gate to SubagentStop so each agent's own work is checked before it reports back; record which agent made each mistake, so agents can be improved
- [ ] Gate verdict isn't logged (an "OK" leaves no trace) and it's inconsistent: on 2026-11-14 a long "…Fixed, it works now." test transcript ran the brain (4,041 tokens) and was NOT blocked, while the implementer's similar test was — log every verdict, then measure block rate on a fixed set
- [ ] T8–T10 — automatic weekly updates, slots + IDEAS rows
- [ ] Knowledge-manager: record in the setup's SDD that the setup is in git (2 repos, what's excluded)

- [ ] review captured case `no-cost-caps-when-user-said-cost-irrelevant` (cases/_pending/no-cost-caps-when-user-said-cost-irrelevant.md): add, edit or discard
- [ ] review captured case `answer-the-direct-question-before-details` (cases/_pending/answer-the-direct-question-before-details.md): add, edit or discard
Done
- [x] 2026-11-14 — gate false block fixed: a background-agent notification now starts a new turn and its result is evidence; "Stop hook feedback" no longer counts as his message. Replayed the false-block transcript 3×: no block (brain consulted each time)
- [x] 2026-11-13 — every project keeps a Todo (fifth document): CLAUDE.md + knowledge-manager rules
- [x] 2026-11-13 — `self_improving_harness` (public) and `work_knowledge` (private) pushed; security scan before the first push
