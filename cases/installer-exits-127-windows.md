---
id: installer-exits-127-windows
date: (not stated; recorded as blocked in IDEAS.md)
level: advice
source: Vault/Projects/Claude_Setup/IDEAS.md (row "Persistent memory across sessions")
situation:
  - "install claude-mem for persistent memory across sessions"
  - "add a memory plugin; the installer is not working on Windows"
  - "the installer finished with no error but nothing was installed"
  - "retry the install with npx / global / bun"
wrong: Tried the installer three ways (npx, global, with Bun). Each exited 127 silently after "Copying to marketplace directory". Retrying the same install in new wrappers does not change that.
right: After one failed variant, stop retrying. Report the exact exit code and last log line, mark the idea blocked, and either debug the installer itself or pick another memory tool.
lesson: When an installer fails the same way in different wrappers, the wrapper is not the cause; stop and debug or switch tools.
replay: "Install claude-mem on this Windows machine. An earlier try with npx exited 127 right after 'Copying to marketplace directory'. Get it working."
pass_if:
  - the answer states that 127 means command not found and that the earlier failure is not fixed by a plain retry
  - it does not just run the same npx install command again as its first action
  - it proposes inspecting the installer step that fails, or an alternative memory tool, or reports the item as blocked
---
