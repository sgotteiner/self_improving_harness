"""Drafts waiting for his word (lesson drafts from capture.py, diary drafts from decisions.py) never interrupt him: they collect
silently, each with its line in the to-do list. At most once a day, on the first message of the day, the hook prints ONE line
saying how many wait; after that nothing, until he asks ("review drafts" -> `drafts.py show`).
A draft that is clearly a false capture (his message was no correction and no decision) the main session may discard without
asking: `drafts.py discard <lesson|diary> <slug> "<why>"` moves it to a `_discarded/` folder next to the drafts (gitignored; his
words stay recoverable) and logs the discard to the setup's flags file with its title and his quoted words, so nothing
disappears silently.
Usage: python -I scripts/recall/drafts.py show | discard <lesson|diary> <slug> "<why it is a false capture>" """
import datetime, os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, diary, index, mdfile, pending

LESSONS = os.path.join(ctx.ROOT, "cases", "_pending")  # = casesave.PENDING, without importing the embedder for one line a day
STATE = os.path.join(tempfile.gettempdir(), "recall-drafts")  # one marker per day


def waiting():
    """(lesson drafts, diary drafts): slugs of the pending files."""
    names = lambda d: [f[:-3] for f in sorted(os.listdir(d)) if f.endswith(".md") and f not in index.NOT_LESSONS] if os.path.isdir(d) else []
    return names(LESSONS), names(diary.PENDING)


def daily_line(today=None):
    """[the one line] on the first call of a day when drafts wait, else []. The day is marked either way: no second line today."""
    day = str(today or datetime.date.today())
    mark = os.path.join(STATE, day + ".done")
    if os.path.exists(mark):
        return []
    os.makedirs(STATE, exist_ok=True)
    for f in os.listdir(STATE):
        if f != day + ".done":
            try:
                os.remove(os.path.join(STATE, f))
            except OSError:
                pass
    open(mark, "w").close()
    lessons, diaries = waiting()
    if not lessons and not diaries:
        return []
    n = len(lessons) + len(diaries)
    return [f"Drafts waiting: {n} ({len(lessons)} lesson, {len(diaries)} diary). Tell the owner exactly this one line, once, and nothing "
            f"more about them: \"{n} drafts waiting ({len(lessons)} lesson, {len(diaries)} diary) - say 'review drafts' to see them\". "
            "When he says 'review drafts': run `python -I scripts/recall/drafts.py show` and go through them with him. A draft that is "
            "clearly a false capture (his message was not a correction or a decision) you may discard without asking: "
            "`python -I scripts/recall/drafts.py discard <lesson|diary> <slug> \"<why it is false>\"` (it logs the discard)."]


def show():
    import capture, decisions
    for _, note in capture.ask_notes(False) + decisions.ask_notes(False):
        print(note + "\n")


def log_discard(kind, slug, why, d=None):
    """Append the discard (with the draft's title and his quoted words) to the setup's flags file under today's
    Claude-on-its-own section; returns True when written."""
    path = diary.flags_for(ctx.ROOT)
    if not path:
        ctx.log(f"drafts: discard of {kind} draft {slug} not logged, the setup has no flags file")
        return False
    import flags
    d = d or {}
    title = str(d.get("title") or d.get("lesson") or slug).replace('"', "'")[:120]
    words = str(d.get("his_words") or "").replace('"', "'").replace(chr(10), " ")[:300]
    item = f'- **discarded the {kind} draft `{slug}` ("{title}") as a false capture ({why}); kept in _discarded/** — owner asked: ' + (f'"{words}"' if words else "(not stated)")
    head = flags.HEADING.format(date=datetime.date.today())
    mdfile.write_atomic(path, mdfile.insert_under(mdfile.read(path), head, item, new_before=flags.BEFORE))
    return True


def discard(kind, slug, why):
    """Log first, then remove: a discard that cannot be logged is refused. Returns the exit code."""
    if kind not in ("lesson", "diary") or not why.strip():
        print("usage: drafts.py discard <lesson|diary> <slug> \"<why it is a false capture>\"")
        return 2
    folder = LESSONS if kind == "lesson" else diary.PENDING
    if not os.path.exists(os.path.join(folder, slug + ".md")) or os.sep in slug or "/" in slug:
        print(f"no {kind} draft {slug}")
        return 0
    src = os.path.join(folder, slug + ".md")
    if not log_discard(kind, slug, why.strip(), index.parse(src)):
        print("not discarded: the flags file is missing, so the discard could not be logged")
        return 1
    os.makedirs(os.path.join(folder, "_discarded"), exist_ok=True)
    os.replace(src, os.path.join(folder, "_discarded", slug + ".md"))
    pending.todo_remove(f"{'cases/_pending' if kind == 'lesson' else 'diary-pending'}/{slug}.md")
    print(f"discarded {kind} draft {slug} (kept in _discarded/), logged in the flags file")
    return 0


if __name__ == "__main__" and len(sys.argv) >= 2:
    if sys.argv[1] == "show":
        show()
    elif sys.argv[1] == "discard":
        sys.exit(discard(*(sys.argv[2:5] + [""] * 3)[:3]))
    else:
        sys.exit(2)
