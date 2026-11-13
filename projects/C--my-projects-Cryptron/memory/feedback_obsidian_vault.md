---
name: feedback-obsidian-vault
description: "Maintain his Obsidian vault (C:\\my_projects\\Vault) automatically — knowledge, methodology, conventions; never needs to be asked."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f4f688de-e613-47ee-b566-9b18d63dd04d
---

The user's Obsidian vault at `C:\my_projects\Vault` is his second brain: extracted knowledge (`Code_Practices/`), conventions (`Code_Conventions/Coding_Assistant_Rules.md` — separation of concerns, files ≤150 lines), per-project notes (`Projects/<Name>/`), and `Dashboard.md` as the index. He explicitly does NOT want to tell each session to use/maintain it — sessions must pick this up themselves (a global `~/.claude/CLAUDE.md` was created 2026-07-09 encoding this; keep it working).

**Why:** "make sure my work is not wasted" — knowledge gained, work methodology, and technical conventions must persist across sessions and projects.

**How to apply:** read the vault conventions before coding; after durable work, write knowledge/decisions into the vault (frontmatter tags, `[[wiki-links]]`, update `Dashboard.md` links); mark superseded notes rather than leaving two truths. For Cryptron: repo `docs/` is the source of truth, vault notes summarize + link ([[cryptron-core-thesis]]).

Note: his old rules file has a "strict approval protocol" (rule 3, from Antigravity days) that conflicts with how he works with Claude Code (autonomous "start doing it"); flagged to him 2026-07-09 — follow the session's permission mode unless he says otherwise.
