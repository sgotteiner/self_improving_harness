"""Decision capture (switch `decision-capture` in slots.json). Mirrors mistake capture (capture.py): on his message a
cheap model detects a design decision (a rule for how something should work, a choice between options, a yes to a design
the assistant just proposed); if so a second call drafts a diary entry into diary-pending/ (local only: that folder is
not in the .gitignore allowlist, so the public setup repo never sees his words); the next message presents it once
("Diary: <title> - '<his words>'. Add it?"); his yes -> `decisions.py approve <slug>` appends it to the project's diary
in the design-diary format (diary.py), his no -> `discard <slug>`. The rule it serves (CLAUDE.md): the diary is
append-only, suggested in one line, appended only after his yes. Why a hook: the entry used to depend on the main
session remembering to suggest it, and the setup's diary went 3 weeks without one."""
import datetime, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain, ctx, diary, grounding, pending, setupstate

NOT_STATED = "(not stated)"

DETECT = ("The assistant's previous turn:\n{prev}\n\nThe owner's new message: {prompt}\n\n"
          "Does his message state a DESIGN decision or approve one: a rule for how something should work or be built, a "
          "choice between options (also a bare 'a.' / 'option 2' picking one of the assistant's options), or a 'yes' / 'ok' / "
          "'do it' to a design the assistant just proposed? A message that ALSO asks a question is still YES when another "
          "part of it states or picks a decision. NOT a decision: a bug report or 'it doesn't work', only a question, a "
          "correction of the assistant's behavior or mistake ('I told you', 'that's wrong', 'you missed'), an instruction "
          "for one task ('make the button blue', 'rename it', 'fix that'), a yes to a code fix or a plain action (run it, "
          "commit it), approval of a finished result, thanks. Reply 'NO' or 'YES | <one sentence: the decision>'.")
DRAFT = ("Draft a design-diary entry for this decision of the owner. Decision: {why}\nThe assistant's previous turn "
         "(context only):\n{prev}\nThe owner's words: {prompt}\n\nReply with JSON only: {{\"title\": \"short title of the "
         "decision\", \"idea\": \"what he decided, 1-2 sentences, in design terms (include the design the assistant "
         "proposed if he said yes to it)\", \"why\": \"the reasoning, quoting HIS words that state it; if he gave no "
         "reason write '(not stated)'; never invent a reason\", \"kind\": \"decision|principle|feature-motivation\", "
         "\"portable\": \"yes|no (would it apply in other projects)\", \"importance\": \"normal|high\", \"about\": \"setup|project (setup = the decision is about the Claude Code setup "
         "itself: hooks, agents, skills, CLAUDE.md, settings, cases, the diary mechanism; project = about the work "
         "project's own system)\"}}.")


def grounded(why, prompt):
    """True when `why` repeats a span of his message (grounding.MIN_SPAN_WORDS words; a message under
    MIN_MESSAGE_WORDS words grounds nothing): a why he did not say is invented."""
    return bool(grounding.common_span(why, prompt))


def process(prompt, tp):
    """On a new human prompt. Returns (path of a new draft or None, brain tokens).
    Detection also runs when the previous turn is empty (his first message may state a rule): mistake capture skips that
    case (nothing to correct), so there is still one detection call, not two."""
    prev, tools = ctx.last_turn(tp, prompt.strip())
    if "Add it?" in prev and "Diary:" in prev:  # his message answers a diary question; it is not a decision
        return None, 0
    out, tok = brain.ask(DETECT.format(prev=prev or "(none)", prompt=prompt), tag="decision-detect")
    if not out.upper().startswith("YES"):
        return None, tok
    raw, t2 = brain.ask(DRAFT.format(why=out.partition("|")[2].strip(), prev=prev or "(none)", prompt=prompt), tag="decision-draft")
    tok += t2
    d = pending.json_of(raw)
    if not d or not d.get("title") or not d.get("idea"):
        return None, tok
    why = str(d.get("why") or NOT_STATED).strip()
    if why != NOT_STATED and not grounded(why, prompt):
        ctx.log(f"decisions: why not from his words, set to {NOT_STATED}: {why}")
        why = NOT_STATED
    # the session's folder is not always what the decision is about: a decision about the setup (the brain says so, or the
    # turn edited setup files) goes to the setup's diary even when the session runs in a work project's folder
    about_setup = str(d.get("about", "")).lower().startswith("setup") or setupstate.setup_edited(tp, prompt.strip())
    cwd = ctx.ROOT if about_setup else diary.project_of(tp)
    target = diary.diary_for(cwd)
    dup = diary.duplicate(d["title"], d["idea"], target)
    if dup:
        ctx.log(f"decisions: skipped, matches {dup[0]} at {dup[1]:.2f}")
        return None, tok
    slug = pending.slugify(d["title"], "decision")
    path = os.path.join(diary.PENDING, slug + ".md")
    os.makedirs(diary.PENDING, exist_ok=True)
    q = pending.q
    kind = d.get("kind") if d.get("kind") in ("decision", "principle", "feature-motivation") else "decision"
    body = (f"---\nid: {slug}\ndate: {datetime.date.today()}\nproject: {q(cwd)}\ntarget: {q(target)}\n"
            f"session: {os.path.splitext(os.path.basename(tp))[0][:8]}\nstatus: pending\nasked: false\n"
            f"title: {q(d['title'])}\nkind: {kind}\nportable: {'yes' if str(d.get('portable')).lower().startswith('y') else 'no'}\n"
            f"importance: {'high' if str(d.get('importance')).lower() == 'high' else 'normal'}\n"
            f"idea: {q(d['idea'])}\nwhy: {q(why)}\nhis_words: {q(prompt.strip())}\n---\n")
    open(path, "w", encoding="utf-8").write(body)
    try:
        pending.todo_add(f"- [ ] diary entry suggested `{slug}` (diary-pending/{slug}.md): add or discard")
    except OSError as e:
        ctx.log(f"decisions: todo not updated: {e!r}")
    return path, tok


def _note(slug, d):
    return (f"Diary: {d.get('title', '')} - '{d.get('his_words', '')}'. Add it? Ask the owner exactly this one line (the "
            f"rule: append to the diary only after his yes). If he says yes run `python -I scripts/recall/decisions.py "
            f"approve {slug}`; if no, `python -I scripts/recall/decisions.py discard {slug}`; no answer: leave it.")


def ask_notes():
    """[(path, note)] for each draft not yet asked about; hook.py prints them and then calls pending.mark_asked(path)."""
    return pending.ask_notes(diary.PENDING, _note)


if __name__ == "__main__" and len(sys.argv) >= 3 and sys.argv[1] in ("approve", "discard"):
    sys.exit(diary.approve(*sys.argv[2:4]) if sys.argv[1] == "approve" else diary.discard(sys.argv[2]))
