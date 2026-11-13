---
name: vault
description: The owner's Obsidian vault rules (C:\my_projects\Vault) - note kinds, project notes and their State section, conventions, superseding stale notes, design diaries. Use whenever writing or updating anything in the vault.
---

# The knowledge vault — rules

`C:\my_projects\Vault` is the owner's second brain. Full rules: `Vault/Meta/Documentation_Methodology.md`.

1. **Code baseline:** `Vault/Code_Conventions/Coding_Assistant_Rules.md` (separation of concerns;
   files ≤150 lines — split when bigger).

2. **Two kinds of notes:**
   - **Domain notes** — reusable, cross-project: `Code_Practices/`, `Backend_Decisions/`,
     `UI_Tips/`, `Security/`, `Web_Performance/`, `Docker/`, `Testing/`, `Logging_and_Debugging/`,
     `MCPs/`. One note = one coherent idea; the title names the thing, not the project.
   - **Project notes** — one per project, `Projects/<Name>/Project.md`, **self-contained** (the
     full record lives in the vault, so it can go to the cloud without the code; duplicating repo
     docs is fine). Sections from `Vault/Meta/_Project_Template.md`: What it is · Tech stack ·
     Key decisions (with *why*) · **State (✅ done / 🔨 in progress / ⬜ next)** · Extracted
     knowledge · Source.

3. **Document as part of finishing.** A decision, a lesson, a state change → write or update the
   note before the session ends. Keep the project note's **State** current; a stale State means
   the note failed its job.

4. **Conventions:** frontmatter `tags: [...]`; `[[wiki-links]]` between related notes; keep
   `Dashboard.md` links live. **No empty stub notes** — fill or omit.

5. **Stale notes are harmful.** When work supersedes a note, mark it
   `> [!warning] Superseded by [[...]]` and link the replacement. Never two truths about the
   current state — but keep the superseded design's *why*.

6. **The design diary.** Every project keeps an append-only `DESIGN_DECISIONS_DIARY.md` beside its
   design doc: the design doc is the current WHAT (edited freely), the diary is the WHY (dated,
   never edited or deleted). Decisions only — design, architecture or development choices, with
   the why, and on a change why the old approach was left. No routine implementation. The project
   note's Key decisions is the distilled highlight reel. Method: the `design-diary` skill.
