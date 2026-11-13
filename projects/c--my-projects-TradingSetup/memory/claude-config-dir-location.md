---
name: claude-config-dir-location
description: "Claude Code config lives at C:\\my_projects\\.claude-config, not the user folder; pending check after the 2026-09-21 VS Code restart"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8ae67f51-8619-418a-ae02-075d7ee51e88
  modified: 2026-09-21T15:40:58.861Z
---

Claude Code's config directory on this machine is `C:\my_projects\.claude-config`,
set via `CLAUDE_CONFIG_DIR` in `HKCU\Environment` (2026-09-21). It holds settings,
credentials, transcripts, skills, plugins and memory. The user does not want any
Claude config in the home folder.

**Why:** the home folder is `C:\Users\שגיא`, and its Hebrew name breaks path
handling — the model picker failed with `Failed to set model: EPERM ... mkdir
'C:\Users\איגש'`, the folder name reversed into a path that does not exist. See
[[hebrew-path-shell-bug]].

**How to apply:** On 2026-09-21 the variable was set at user level specifically so the
VS Code **extension host** inherits it — the `claudeCode.environmentVariables` setting
only reaches the process the extension spawns, so the host kept writing its IDE lock
to the old folder. This was set but never verified, because verifying needs a full
VS Code restart.

**Verified 2026-09-21 18:39:** after a full VS Code restart the IDE lock (57994.lock)
was written to `C:\my_projects\.claude-config\ide\`; the old `ide\` folder is empty and
nothing in the old folder was written after 18:30. The old `C:\Users\D154~1\.claude`
is now unused. The user said not to delete it (2026-09-21) — leave it in place and
don't offer to remove it again.
