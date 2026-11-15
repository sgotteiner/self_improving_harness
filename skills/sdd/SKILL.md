---
name: sdd
description: The format of a project's SDD (the current state of its features, logic and how they connect) and how to update it. Use when you write, update or check an SDD, or generate the system map from it. One heading tree; every section has the same fields; a validator and a map generator read it.
---

# SDD format

**Why (his words):** "the sdd holds the current state of the project with its features and logic and how everything connects. different features different sections with what are they, why were they added, what other features relate to it, maybe also smaller details like the map has nesting. then maps will easily read it and make the maps. updates either add a new section or change one at the right level. notice the nesting consistency. i like things are well explained but i want to choose how much far i want to dive in and nesting is the choice. the diagram just visualizes it."
On timing: "we write code check stuff until i like it and approve and only then sdd". The SDD is written after he approves a change, never while it is still being tried.

## 1. What the SDD is
The current, approved state of the project: its features, their logic, and how they connect. Nothing in progress, no history. History and the reasons behind decisions live in the diary; open work lives in the ideas file and the todo.

## 2. Shape: one tree, nested by headings
- One heading per feature; its parts are sub-headings under it; their details are sub-sub-headings. Heading depth is nesting depth (`##` top features, `###` their parts, `####` details, deeper if needed). `#` is the project title, once.
- **Consistency rule:** siblings sit at the same level of detail. A section as specific as another section's children belongs one level down. The top level is the few big features (or, for a process, its stages), most general first.
- Sections are in the order things happen where there is a flow; otherwise in the order of importance.

## 3. Every section, at every level, has the same fields
Right under its heading, one per line, in this order, then a blank line:

```
## <Title>
id: <stable-kebab-id>            (never changes when the title is renamed)
feature: <what it is / what happens here, in plain words>   (the map box shows this)
after: <id>                       (only if it is a step in a flow: the step before it)
related: <id>, <id>               (features it uses or affects; the map draws these as links)
value: <what problem it solves, what it brings> — diary: <entry title>   (features)
open: <what is not known>         (only if something is unknown)
tag: <short label>                (optional; the map shows it under the name)

<what it is and how it works: short prose, plain words>

- criteria: <the real values and the setting that changes each>   (detail levels)
- files: <path>, <path>
```
- A field value continues on the next line if that line is indented.
- **Length:** no fixed length. Each field answers its question correctly and fully at its level: `feature` says what it is / what happens here; `value` says what value it brings and what problem it solves. If the answer grows too long for its level, the detail moves one level down into a sub-section. (His words: "summary and why dont have to be one sentence ... it should answer correctly. too long you can go down a level. the why tells the value of the feature, what problem it solves.") Short but never missing: every part is present and non-empty.
- Field names are his: `feature` (not "summary"), `value` (not "why").
- Upper levels: feature, what and how, value, related. Lower levels add the criteria, numbers and files.
- Plain words at the top; names of code, numbers and paths only from the second level down (the validator checks the top level).
- Unknown: a line `open: <what is not known>` (the map shows it in red), never a guess.
- The project title (`#`) may carry `feature:` (one plain sentence about the whole project) and `open:`; it needs no id.

## 4. Updating (after he approves a change: "done")
1. Find the section(s) the approved change touches, by id.
2. **Change them in place**, at their level: edit the fields that changed; add a new section for a new part, under its parent, at the right depth; delete the section of a removed part (and its id from every `related` and `after`).
3. Never append history ("changed on...", "was X, now Y"). That goes to the diary, if he approves an entry.
4. Run the validator: `node skills/sdd/scripts/validate-sdd.js <sdd.md> --since <last-commit>`; add `--removed <id,id>` for a part deleted on purpose. Fix every problem it lists.
5. Commit the SDD with the why. Then the map is regenerated (section 6).

## 5. Validator
`node skills/sdd/scripts/validate-sdd.js <sdd.md> [--since <commit>] [--removed <ids>]` fails, naming the heading and line, when:
- a section has no `id` or no `feature`, an id is not kebab-case, or an id is duplicated;
- a `related` or `after` names an id that does not exist, or an `after` chain loops;
- with `--since`: an id present at that commit is gone (a rename must keep the id) and was not listed in `--removed`;
- a top-level (`##`) feature text has digits, a path or file name, or a code name;
- a section lists criteria or files but has no feature or what/how above them;
- a line under a heading is not a field, a field is unknown or given twice, or a heading level is skipped.

## 6. The map
`node skills/sdd/scripts/sdd-to-map.js <sdd.md> <map.html> [--template <template.html>] [--commit <id>]` reads the SDD (the working tree, which must be committed; or the SDD as it was at `--commit`) and writes the map's data `T`: one box per section, nested the same way. Box name = heading, `desc` = `feature`, `facts` = value, what/how and criteria lines, `file` = the files line, `talks` = `related`, order = `after`, `note` = `open`, `tag` = `tag`, `sdd` = the heading. The root records `sdd` (the file) and `sddCommit` (the commit it was drawn from). Top-level sections that are steps of a flow (`after`) go to the flow lane, the others to the support lane. If the map file exists only its `T` is replaced; otherwise it starts from the system-map template. No agent and no guessing: the same SDD gives a byte-identical map, and changing one section changes one box.
Regenerate after every SDD commit, or when he asks. Check with `node skills/system-map/scripts/check-structure.js <map.html>`.

Tests of these tools: `node skills/sdd/scripts/test-sdd.js` (fixtures in `skills/sdd/scripts/fixtures/`; `make-broken-fixtures.js` rebuilds the broken ones from `good.md`).

## Not decided yet
Projects with several SDD files (one project has three): decided when that project is converted. His words: "well get to that when i get to this project its very complicated".
