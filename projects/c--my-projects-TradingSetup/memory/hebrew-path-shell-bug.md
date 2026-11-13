---
name: hebrew-path-shell-bug
description: Hebrew characters in Bash commands break the shell wrapper on this machine; use the 8.3 short name C:\Users\D154~1 instead of C:\Users\שגיא
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8ae67f51-8619-418a-ae02-075d7ee51e88
  modified: 2026-09-21T15:37:00.522Z
---

Never type the Hebrew username path `C:\Users\שגיא` into a Bash command on this
machine. Use the 8.3 short name `C:\Users\D154~1` instead, or avoid the folder
entirely.

**Why:** Hebrew characters in the command string break Claude Code's Bash wrapper —
it fails with `No such file or directory` on its own temp cwd file, before the
command ever runs. Reproduced twice on 2026-09-21. The same right-to-left encoding
class caused the original `Failed to set model: EPERM ... mkdir 'C:\Users\איגש'`
error, where the extension reversed the folder name into a path that does not exist.
The user's standing instruction: "i dont want the hebrew bug dont work in that folder."

**How to apply:** Claude Code's config was moved out of the user folder to
`C:\my_projects\.claude-config` (via `CLAUDE_CONFIG_DIR`), so there is normally no
reason to touch the home directory at all. If a command genuinely needs that path,
write it as `/c/Users/D154~1/...` and assign it to a shell variable rather than
repeating it. See [[claude-config-dir-location]].
