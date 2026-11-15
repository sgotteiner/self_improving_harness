---
name: design-diary
description: >-
  Build, backfill, rewrite, or maintain a project's append-only design-decisions
  diary — the WHY-log of the owner's design, reconstructed from git history and
  past chat transcripts. Use this whenever the user wants a DESIGN_DECISIONS_DIARY,
  decision log, design diary, "why log", or a record of the reasoning behind a
  project's decisions — including "backfill the diary", "reconstruct why we chose
  X", "keep a decision diary as we work", or appending a single decision live as
  work happens. Reach for it even when the user only describes the goal (capture
  the thinking behind this project so it isn't lost) without naming a "diary".
---

# Design Diary

A project's design-decisions diary is its **append-only WHY-log**: the *what and
why of the owner's ideas*, kept because the WHAT is re-derivable from code but the
WHY is lost the moment the conversation ends. This skill reconstructs that log from
the raw record of how a project was built — its git history and its past chat
transcripts — and maintains it going forward.

The diary serves two people at once, and both matter:
- **The project** — a memory of what was decided and *why*, so a future session
  never reverts a hard-won decision without knowing what it cost.
- **The developer** — a portable record of their own thinking and their best ideas,
  reusable in other projects, and a record of how they grew.

## What this skill produces

**Two files, kept separate on purpose** — plus tags that do the rest:

1. **The diary** (`docs/DESIGN_DECISIONS_DIARY.md`) — the owner's design decisions
   and their why. **Nothing else.** Its integrity is the thing that matters most.
2. **The flags/debt log** (`docs/DIARY_FLAGS.md`) — a companion holding
   *claude-on-its-own* decisions and *known-but-deferred* problems, so they're
   visible and not lost — without ever corrupting the diary.

The **crown jewels don't get their own file** — the `signature` and `importance`
tags surface them in place, filterable and traceable without proliferating files.

## Prime directives

These override everything below. When a call is hard, resolve it toward these.

- **The owner's ideas are sacred — missing one is the cardinal failure.** The whole
  point of the diary is to preserve the owner's design thinking. An idea that carries
  a why and gets dropped is the one *unrecoverable* loss: the code doesn't hold it and
  the conversation is gone. So bias hard toward capture — when unsure whether a line
  of theirs is an idea, treat it as one until proven trash. Every other rule here
  serves this one.
- **The diary holds only the owner's design.** Never let cleanup of Claude's
  mistakes, routine implementation, or noise sit in the diary dressed as design.
  Miscrediting an autonomous Claude decision — good or bad — as the owner's
  corrupts the one thing the diary is for. Protecting it from corruption outranks
  completeness.
- **It's a WHY-log, not a WHAT-log — and the owner's *how* is also an idea.** Capture
  the idea and the reasoning. When the owner prescribes *how* to do something — a
  method, a mechanism, an approach ("gate with a similarity threshold," "price only
  against stablecoins," "one step at a time, ask what you were taught") — that **how
  is a design idea; keep it.** What you drop as re-derivable is only the *code-level*
  how: table columns, function names, file layout, library choices. The line: a
  **design-how** is a choice that had alternatives and carries a why; an
  **implementation-how** is the mechanical realization with no alternative worth
  recording. Mistaking a design-how for implementation is a common way an idea gets
  silently dropped — don't.
- **Thorough, but filtered.** Read *everything*; account for everything; keep only
  what carries a why (the owner's above all), and drop the rest **on purpose**.
  Missing a real idea starves the diary; keeping a routine fix corrupts it — both
  are failures. A good diary is a *filter*, not an archive.
- **Grounded, never invented.** Every *why* must trace to something the owner
  actually said. If he didn't state it, write `(not stated)` — never an inferred reason
  in his diary; a reason Claude infers goes to the project's flags file as "inferred why
  for <entry title>". Never fabricate a plausible-sounding rationale. A confident wrong why is worse than an
  admitted gap.

## Inputs: read the whole record

- **Git history** — `git log --reverse` for the timeline. Commits are used as
  *corroboration and anchors*, not as the spine (see "Why not commits").
- **All past chat transcripts** — the conversations where the design actually
  happened. This is the primary source: decisions live in the *arguments*, not in
  commit messages.
- **The project's own `.md` docs** — design docs are *content*, read them directly.

**Read everything, including code and `.md` files.** Code pasted into a chat is
usually only a few hundred lines — trivial to read, and seeing what was built often
clarifies the decision. The only thing worth skipping is genuinely voluminous,
low-signal output — **logs**.

Helper scripts (for Claude Code transcripts at `~/.claude/projects/<slug>/*.jsonl`):
- `scripts/list_sessions.py <transcript-dir>` — every session, oldest first, with
  its first message + turn count.
- `scripts/dump_chat.py <transcript-dir> <session-id>` — one session's
  user+assistant prose to a readable file (keeps code fences and docs; drops only
  tool-result noise, which is where logs live).

If the host isn't Claude Code, find wherever the chat history lives and read it in
full.

## Why not commits (the stepping insight)

A commit is a *code-timeline* boundary; a session is a *work-rhythm* boundary. A
**decision respects neither** — it bleeds across several sessions/commits and hides
several-to-one. Any fixed boundary you pick cuts through the middle of some ideas
and lumps others together. So don't step by commit or session. Step by **feature**.

## The method: two passes

### Pass 1 — MAP (build the feature tree)

Read the whole record and segment it by *meaning*, not by proxy:

- A **feature** is a coherent unit of work, defined by *the problem being solved*
  ("what are we trying to do right now"). Being semantic, it spans several sessions
  and splits a busy session correctly. This is the natural step boundary.
- A **mini-feature** is a sub-goal dipped into *to unblock the main line*, then
  returned from. The signature that separates it from a *new* feature is **the
  return**: a new goal that returns to the parent is a mini-feature nested under it;
  a new goal that replaces the parent is a new feature. (Examples: a visibility tool
  built to help develop the real feature; a small control option; a new helper —
  each a detour that comes back.)
- Keep nesting to two levels (feature → mini-feature); deeper gets confusing.

Pass 1's output is a tree — features → mini-features → the candidate ideas inside,
each with pointers to where it's discussed (`session:turn`, commit). This tree is
three things at once: the diary's **skeleton**, the **review checkpoint** (in
attended mode, confirm the tree before writing), and the answer to "ideas span and
split sessions" (a feature gathers its scattered touchpoints).

### Pass 2 — WRITE (one node at a time)

For each node, gather its touchpoints, read them together, and write the entries —
the *ideas + whys* inside that feature. Nest a mini-feature's entries under its
parent, at the point it happened.

## The owner's ideas come first — before flags, before attribution

The owner's ideas are the sacred core (first prime directive), so the write is
**ordered** to protect them — attention spent on anything else must not be allowed to
eat one:

1. **Extract the owner's ideas first, exhaustively.** Read their messages asking only
   *"what are they designing, deciding, or prescribing here?"* — the what, the why,
   and the **how** (a method or mechanism they chose is an idea). Capture every one
   before looking at anything else.
2. **Only then apply the flag / attribution lens** — *"what did Claude do on its own?
   what's debt?"* A flag can **never** consume an idea it's tangled with. When the
   owner's mechanism and Claude's botched realization share a breath (e.g. "gate with
   a similarity threshold" *and* a magic value shipped untested), that is **two
   records** — the idea in the diary, the flag in the debt log — never one.
3. **Account for every owner message.** Each maps to an idea, a flag, or a deliberate
   skip-with-reason. Nothing the owner said is silently dropped; an idea can't
   evaporate just because attention was elsewhere (a juicy flag, an implementation
   detail, a vivid example). Ideas are extracted first so nothing else can claim them.

## Filtering: mine wide or narrow by the mode of work

The biggest tell for where the *why* lives is **the mode of work** in that stretch:

- **Design / develop mode** (functionality, architecture, implementation,
  visibility — building forward) → signal-dense. **Mine it wide.**
- **Testing / cleaning mode** (debugging, fixing, cleanup) → mostly trash *for the
  diary*. **Mine it narrow** — but do **not** blanket-skip it, because when the
  owner corrects Claude they often explain the *design* behind why something was
  wrong, and that explanation is a real why. Those are **gems buried in cleanup**:
  take the design-why, discard the debugging around it.

Earns an entry: a design/architecture/development **choice, or an idea, that
carries a why** — general and decision-moving. Doesn't: routine implementation,
env/setup, scaffolding, doc tidying, dead-ends. No why → no entry.

## Examples: the demonstration vs. the design

This owner (and many like them) thinks in **examples** — often an example is how a
hard idea gets expressed at all. Tell the two kinds apart, because they're handled
oppositely:

- **Load-bearing example — the example *is* the design.** When defining something is
  hard and they instead *show* it — how they research a coin, what looks "fishy" to
  them, how they'd trade a case — that example is the **clearest design content there
  is**, often their signature thinking. Capture it faithfully; do not summarize it
  away. A load-bearing example *defines* something they couldn't otherwise say.
- **Illustrative example — a "for instance" for a small point.** The point stands
  without it; the example is just a demo. Capture the **point**; let the example
  appear lightly if it helps, but **never calcify its incidental specifics as spec**.
  An illustrative example *supports* something they already said.

The failure to avoid is **hardening a demo into a conclusion**. If they say "1H
worked, 4H worked better, so try daily" to show a *reasoning move* (follow the
gradient), record the move — not "the answer is 4H." Reifying the instance turns a
demonstration into a rule they never made.

## Attribution: whose idea was it?

Every entry carries an attribution — the diary's value to the developer depends on
honestly reflecting *their* thinking:

- **your-design** — the owner designed or requested it.
- **your-correction** — the owner redirected something (itself a design act).
- **delegated** — the owner gave a broad request and let Claude decide, and it stood.
- **claude-on-its-own** — Claude decided something the owner never asked for. **This
  does not go in the diary.** It goes to the flags log. If a later fix of it taught
  a *portable rule*, keep the *rule* (credited to no one's design), not the event.

The honest framing of a claude-on-its-own discovery reads as a **finding**, not a
decision: *"Discovered Claude had done X on its own → changed to Y → why: Z."* If
the honest version comes out as a finding rather than a decision, it belongs in
flags, not the diary.

## Channels: what goes where (keep the diary pure)

| Content | Home |
|---|---|
| The owner's design decisions + why | **Diary** |
| Claude-on-its-own decisions; known-but-deferred problems ("done rough, kept for momentum") | **Flags/debt log** |
| A portable lesson distilled from anywhere (whoever caused it) | The project's **knowledge vault / docs** (title names the *thing*, not the project) |
| Current spec / requirements as they stand | The **design doc** |
| Current project state / status | The **project note** |
| Things still to do | A **todo list** |

Recording claude-on-its-own and known-debt in the flags log — especially in live
mode — doubles as an audit: it surfaces overreaches and lurking problems *as they
happen*, without one of them touching the diary.

## The entry format

One **unified format** for every kind of entry (no per-type templates — they bloat
and fragment). The *type* is a set of tags, not a different shape.

```
### <short title — the idea in a phrase>
tags: kind=<decision|feature-motivation|mini-feature|bug-lesson|principle|milestone|idea> · attribution=<your-design|your-correction|delegated> · portable=<yes|no> · signature=<yes|no> · importance=<high|normal>
anchor: <YYYY-MM-DD> · <commit-or-none> · <session:turn>
**Idea:** <the WHAT *or the HOW* — the decision, or the method/mechanism the owner prescribed, in concept terms, 1–3 sentences>
**Why:** <the reasoning — the problem it solved, the alternative rejected. Summarize in clean prose and cite the source; quote only a signature line. If he didn't state it, write "(not stated)"; an inferred reason goes to the flags file, never here.>
**Replaces:** <only if it supersedes an earlier decision — name it + why the old one was left>
**Links:** [[related entries]]
```

Keep **Idea** tight and **Why** the body. Drop implementation unless a mechanic
*carries* a why (e.g. "rendered canonically so two records don't split on
name-noise" is really a why — keep that; drop the class names).

**Example:**
```
### The situation graph — memory becomes the policy
tags: kind=decision · attribution=your-design · portable=yes · signature=yes · importance=high
anchor: 2026-07-18 · 0153f04 · <session:turn>
**Idea:** The brain takes one step at a time and asks "I'm in this situation — what did my master teach me?", looking the answer up by similarity in a graph of taught (situation → next step) edges. The model only judges the final result; the walk is embed-and-compare.
**Why:** Every failure came from *freedom* — free choice of tool/args/order let it invent things and wander. The sequence of checks should be what the owner taught, not what the model re-decides each turn. Memory as policy, not a prompt re-deciding every move.
**Links:** [[the situation graph reopened — the profiler pivot]]
```

## Crown jewels: surface important and interesting via tags

Buried ideas are lost ideas — but the fix is **tags, not another file**. Mark the
standout entries so they can be filtered and traced in place, along two axes:

- **importance=high** — load-bearing decisions the project stands on.
- **signature=yes** — genuinely novel or beautiful ideas, the developer's best
  thinking (and the `portable=yes` ones travel to other projects).

A reader or a later session finds the crown jewels by filtering on these tags — no
curated index file to maintain or let drift.

**Detecting signature ideas:** the owner often flags them explicitly — *"isn't this
a beautiful idea?"*, *"don't you think I'm a genius?"*, *"this is the elegant
part."* Treat those as strong signals. But tag the cool stuff **on your own
judgment too**, even when they didn't say it out loud — a genuinely novel mechanism
or a cross-domain idea is signature whether or not it got a fanfare.

## Grounding, quoting & citation

Anchor each entry to `commit + session:turn` so any claim is verifiable without
re-deriving it. An unstated why is marked `(not stated)`, never invented or inferred in the diary. This makes
the diary self-auditing — the owner can spot-check a citation any time, which is
what lets the **backfill** run **unattended** (live mode is approval-gated — see Modes).

**Verify anchors against git — never guess a nearby hash.** A citation exists to be
*checked*, so a wrong one is a grounding failure. When a decision lives in a doc/file,
find the commit that actually introduced it with `git log --diff-filter=A -- <path>`,
not a commit that merely sits near it in time. Whenever you pin a hash, confirm its
subject matches the entry's topic (`git show -s --format=%s <hash>`). A
plausible-but-wrong anchor stays silent until someone checks it — so check.

**Summarize by default; quote rarely.** The chat and the diary are different
registers: the owner's real-time language is precise — often the best expression of
the idea — but it's *thinking in motion*, embedded in the flow of work. The diary
row is the *settled distillation*. Render the why in clean diary prose **plus the
citation** (the original is one click away, checkable) rather than pasting the
transcript. Reserve a **verbatim quote for the rare line where the exact words are
the value** — a signature crystallization, a "beautiful idea" moment.

The unifying rule for both quotes and examples: **preserve verbatim only where the
exact expression is itself the design** (a load-bearing example, a signature line);
**summarize everywhere else, always cited.** Over-quoting is a top cause of bloated,
wall-of-text entries — distillation is what keeps the diary a filter, not a
transcript.

## Modes

- **Backfill** — reconstruct the whole diary from history. Runs **unattended**
  (grounding replaces approval). Read all → map the feature tree → write. Offer to
  confirm the tree first if the owner wants a checkpoint.
- **Live / real-time — a different job from backfill; suggest, never append
  silently.** Backfill looks *backward* at finished work, so "after a feature is done"
  is a real boundary there. **Live has no such view:** you are not in the owner's
  head, you can't see when something is "done," and he does *not* announce
  mini-features. So do **not** wait for a feature to finish. Instead:
  - **Trigger on the idea, not the feature.** When the owner *articulates* a design
    decision — an idea with a why, a design-how, a principle — that single idea is
    capturable on its own (an entry is one idea, not a whole feature). His explicit
    completion signals ("memory is done", "this is the working base") are strong cues
    for milestones/big features — but most decisions won't carry one, especially
    mini-features, so rely on the idea being *stated*, not on a boundary you can't see.
  - **He gates "settled?", not you.** Suggest in one line ("worth logging: <the idea>
    — append it?") and **wait**. He approves, or says wait (still cooking, or more is
    coming — only he knows). Never bank a half-formed decision.
  - **Capture now, structure later.** Approved live entries land as a **chronological
    stream** (anchored `(chat, no commit)`); the feature-tree nesting and mini-feature
    grouping are imposed by a later backfill/reorg pass — you can't build the tree while
    a feature is still open. This is the owner's own *capture-raw-now, structure-later*
    rule (the ephemeral-data principle) turned on the diary: grab the perishable idea
    the moment it's said; give it its place once the shape is visible.
  Route any claude-on-its-own or known-debt to the flags log as it occurs — live
  appending doubles as a real-time audit.

## Structure & ordering

Features are sections in chronological order; mini-features nest under their parent
at the point they happened; entries within a feature run in the order the ideas
arrived. A one-line "why this feature at all" under a feature heading is welcome
when the motivation isn't obvious from its entries. **Append-only:** once the diary
is the live log, never rewrite or delete an entry — only append. (A from-scratch
backfill is the one time the whole file is written at once.)
