---
name: branches-main-and-develop
description: trading_projects uses exactly two branches — main and develop. Work goes on develop; no feature branches.
metadata: 
  node_type: memory
  type: project
  originSessionId: f2bf353e-f9dc-4ade-9d13-777aa09adb70
  modified: 2026-10-04T20:28:11.910Z
---

**Two branches only, from 2026-10-04:** *"from now on we work with main and develop only."*
Work is committed to `develop` and pushed there; `main` is the stable trunk and only moves when he
says so. Do not create feature branches, and do not leave work on one.

History: the feature branch `regime-key-and-sr-lines` was renamed to `develop` and pushed that day.
Before that, 13 commits of finished work had been sitting on one local branch, **never pushed** —
`origin` held only `main`, at "Added median." A day's work, including the ground truth he had just
recorded by hand, existed on one disk.

**How to apply:** commit to `develop` as work finishes, and offer to push rather than letting it
pile up locally — his ground truth file is in the repo, so an unpushed branch is an unbacked-up
answer key. Pushing is still his call each time, but raise it. Merging `develop` into `main` is his
decision, never automatic. Related: [[drawing-tools-are-the-channel]].
