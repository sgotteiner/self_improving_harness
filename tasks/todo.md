# Self-improving harness — todo

Next things, in order. Done items get checked, not deleted. The plan: [plan.md](plan.md).

- [ ] **Back up the personal files** — on this computer only: the excluded sensitive memories, `Vault/Personal/`, `C:\my_projects\personal\`, the design-diary past conversations. Needs: a private `personal` repo (his), then push.
- [ ] T1 — show one undo working; automatic commit + push (with the pre-push scan) — owned by the setup-manager
- [ ] T2 — setup-manager agent draft, for his review
- [ ] Replay can't show the hook helping yet (4/6 pass with and without it) — his decision on next round: harder cases / fix the 2 failing pass_if / stop here
- [ ] Recall hook fires on background-task notifications (injected all 3 cases on one) — skip non-human prompts
- [ ] Replay costs ~2.5M tokens / $3.70 per run — run only after a rule change; consider Sonnet for replay sessions
- [ ] Reviewer pass on scripts/recall/ (new logic); knowledge-manager: SDD + tests doc (recall eval, replay)
- [ ] T7 — capture hook
- [ ] T8–T10 — automatic weekly updates, slots + IDEAS rows
- [ ] Knowledge-manager: record in the setup's SDD that the setup is in git (2 repos, what's excluded)

Done
- [x] 2026-11-13 — every project keeps a Todo (fifth document): CLAUDE.md + knowledge-manager rules
- [x] 2026-11-13 — `self_improving_harness` (public) and `work_knowledge` (private) pushed; security scan before the first push
