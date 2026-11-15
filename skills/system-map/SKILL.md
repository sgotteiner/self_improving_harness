---
name: system-map
description: Build a clickable nested map of how a system works (a pipeline, a codebase, a setup) as one local HTML file. Use when he asks for a diagram, map, flow or "how does X work" picture of a system. Top level tells the story simply; each click opens how it works in detail.
---

# System map

One nested map gives both: **a simple top level he understands at a glance, and dive-in depth that explains how each part really works.** (His words: "the top level is simple and answers my questions and going deeper explains in more detail and how it works".)

## Output
- One self-contained `.html` file, saved where he keeps the project's docs (the project's `docs/`, or the project's Vault folder). Never a hosted page.
- Start from `assets/template.html`: copy it, keep the rendering code and CSS, replace only the data object `T` (keep the `/* ───────── index` comment right after it) and the header/footer placeholders.
- Open the file in his browser when done, and give him the path.

## Before writing: his questions
Write down the questions he asked (e.g. "where are the hooks, what's remembered, how is it retrieved, when"). The top level must answer each one; if a question has no top-level box, the map is wrong.

## The levels
**Level 0 — the story: the steps.** (His words: "its not a fixed number of boxes as much as it needs to show me the steps in the pipeline".)
- The `flow` lane is the steps of the process, one box per step, named by **what happens** ("Check the facts", "Write the script"), not by the component that does it ("Orchestrator"). The component goes in `tag`. A component that does several steps appears in several step boxes; a step's inside opens the component's detail for that step.
- **General to specific at every level.** (His words: "the more nested the less top and more specific thats the idea".) Level 0 is the few big stages of the whole process, the most general view. Each click splits one stage into its more specific steps, and each step into its details, down to the criteria and numbers. A level never mixes generalities: if a box at level 0 is as specific as its neighbour's children, it belongs one level down.
- No fixed number of boxes: as many as the level's real stages, no more. Things that aren't steps (shared stores, outside services) go in the `support` lane.
- The real order things happen. Check the order against the code: an arrow that tells the wrong order is a bug.
- Shared things everything uses (what's stored, outside services) in the `support` lane. Open questions get one box of their own here, never mixed into the explanation.
- Each box: a plain name (no internal jargon; if the code's name is jargon, put it in `tag`), and `desc` = one everyday sentence answering "what happens here". No numbers, file names or setting names at this level.
- The page opens at level 0 with nothing expanded.

**Level 1 — how it works.** The steps inside each box, in order (`flow: true` when ordered). `desc` still starts with one plain sentence; the specifics go in `facts`.

**Level 2+ — the details.** Every box that says something is checked, matched, scored, filtered, classified, limited, routed, retried, approved, captured or stored states, read from the source:
- the criteria (what passes, what fails, how it decides),
- the real numbers (thresholds, caps, schedules, defaults) and the setting that changes each,
- a concrete example from the code, its tests or comments,
- where it lives (`file`) and who/what changes it.
Unknown → a red `note`, never a guess. Code defaults are labelled as defaults.

**Generate, don't retype:** when the substance sits in a data/config file (a rulebook, a list, a prompt), build that branch with a small script saved next to the map (`map-src/`), so it can be refreshed.

## Updating an existing map (never rebuild it)
When the system changed, update only what the change touched:
0. Copy the map aside first (the "before" for step 5).
1. List what changed (files, settings, behavior) from the change itself or git.
2. Find the boxes it touches: every box whose `file` names a changed file, plus boxes whose text mentions the changed part — grep the `T` data for its names, its neighbours' names, and any count or number the change moves (e.g. "27 folders" when a folder is added).
3. Re-read only those sources; edit only those boxes (add a box for a new part, under the stage it belongs to; remove one for a removed part). Re-count every count the change moves. Keep every other box and every id byte-identical.
4. Re-run any generator in `map-src/` whose source changed.
5. Report the diff with `node scripts/diff-maps.js <before> <after>`: identical / changed / added / removed, plus one line per changed box. If more than a third of the boxes changed, stop and ask him before going on.

## Checks before handing it over
1. `node scripts/check-structure.js <map.html>` → "structure ok".
2. `node scripts/audit-vague.js <map.html>` → 0 vague and 0 thin (or each has a red note).
3. Level-0 review by hand: each top box's desc is one plain sentence with no digits, paths or code names; every question of his has a top-level box; the flow order matches the code.
4. Open it in a browser and look at level 0 and one full dive.
