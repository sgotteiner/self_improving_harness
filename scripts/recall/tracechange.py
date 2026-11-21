"""What the message step's TRACE line and the Stop hook's events do to the traces store (tracing.py): open, attach to and close a
trace, add events found by code, hand the closed trace to the work review once. A trace belongs to the session (transcript path) that
opened it: only that session's open traces get a correction, a done or an event. Every function fails open."""
import datetime, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capowed, ctx, tracing
from tracing import NEW, NONE, NO_WHY, SEP, SITUATION, TITLE_MAX, WHY_MAX, add_event, change, flat, latest_open, mine, project, read, render


def ask(fn, tp, text, prompt, tag, reply):
    """The message step's one model call with the trace section added to `text`: fn(tp, text, tag, reply).
    -> (the reply without its TRACE line, tokens, trace(kind, done) which applies that line -> [the record instruction] or [])."""
    try:
        proj = project(tp)  # once for the whole step
    except Exception as e:
        ctx.log(f"tracing: project not found: {e!r}")
        proj = ""
    out, tok = fn(tp, text + tracing.ask_text(tp, proj, prompt), tag, reply)
    out, tline = tracing.take(out)  # its title and why quote must not be read as kind or flags
    return out, tok, lambda kind, done: apply(tp, proj, tline, kind, prompt, done)


def apply(tp, proj, tline, kind, prompt, done):
    """Open, attach to or close a trace from the message step's TRACE line. -> [the one 'record this trace' instruction] when this
    message (DONE) closed a trace, else []."""
    try:
        if not proj:
            return []
        head, _, rest = tline.partition(SEP)
        word = head.strip().strip("`*<>.,")
        if word.upper() == NEW:
            title, _, why = rest.partition(SEP)
            frm = ""
            if ctx.enabled(tracing.LINK_SLOT):  # only a last part that is exactly a FROM leaves the why; a `|` in the why stays
                head, sep, last = why.rpartition(SEP)
                if sep and tracing.FROM_PART.fullmatch(last.strip(" `*.")):
                    why, frm = head, last
            if not title.strip():
                return []
            def make(rows):
                src = tracing.origin(rows, tp, frm) if ctx.enabled(tracing.LINK_SLOT) else None  # before the new row: it is not its own origin
                rows.append(dict(tid=f"t{len(rows) + 1}", project=proj, session=tp, title=flat(title, TITLE_MAX),
                                 why=flat(why.strip(" `*") or NO_WHY, WHY_MAX), opened=str(datetime.date.today()), events=[], closed=None,
                                 **({"from": src} if src else {})))
            change(proj, make)
            return []
        def attach(rows):
            op = mine(rows, tp)
            r = next((x for x in op if x["tid"].lower() == word.lower()), None)
            if not r and word.upper() != NONE:  # no tid: a correction goes to the latest open trace, a done to the only one
                r = latest_open(rows, tp) if kind == "CORRECTION" else op[0] if done and len(op) == 1 else None
            if not r:
                return []
            mark = kind == "CORRECTION" and ctx.enabled(tracing.LINK_SLOT)  # the key lets the write that pays this message find the event
            add_event(r, tp, "correction" if kind == "CORRECTION" else "done" if done else "message", prompt,
                      capowed.key(tp, prompt) if mark else "")
            if not done:
                return []
            r["closed"] = str(datetime.date.today())
            return [("Feature trace closed: call the knowledge-manager now with this trace, for the Ideas row (problem, what was tried, "
                     "result, next; write the trace's Interventions count into the row's result) and, if the system changed, the SDD. The hooks do not edit the vault.\n" + render(r))]
        return change(proj, attach)
    except Exception as e:
        ctx.log(f"tracing: apply failed: {e!r}")
        return []


def add_events(tp, proj, evs):
    """Add (key, type, text) events found by code to the latest open trace of this session; a key already there is skipped."""
    try:
        if not proj or not evs:
            return
        def put(rows):
            r = latest_open(rows, tp)
            if not r:  # it vanished (closed or abandoned) since the caller looked
                return
            have = {e.get("k") for e in r["events"]}
            for k, typ, text in evs:
                if k not in have:
                    add_event(r, tp, typ, text, k)
        change(proj, put)
    except Exception as e:
        ctx.log(f"tracing: events failed: {e!r}")


def link_situations(paid, sids, source, lesson_id):
    """Add the sids of the situations a capture write just stored (`paid` = capowed.pay's marker, or a proposal's {tp, key}) to the
    correction event of his message that owed the write, in whichever open trace of the session holds it; none -> a new `situation`
    event on the latest open trace."""
    try:
        sids = [s for s in sids if s]
        if not (sids and paid and ctx.enabled(tracing.LINK_SLOT)):
            return
        tp = paid["tp"]
        proj = project(tp)
        if not proj:
            return
        def put(rows):
            ev = next((e for r in reversed(mine(rows, tp)) for e in r["events"]
                       if source == "correction" and e["type"] == "correction" and paid.get("key") and e.get("k") == paid["key"]), None)
            if not ev:
                r = latest_open(rows, tp)
                if not r:
                    return
                add_event(r, tp, SITUATION, f"{source}: {lesson_id or 'new lesson'}", f"{SITUATION}|{sids[0]}")
                ev = r["events"][-1]
            ev["sids"] = [*ev.get("sids", []), *sids]
        change(proj, put)
    except Exception as e:
        ctx.log(f"tracing: situation link failed: {e!r}")


def take_closed(tp):
    """The text of this session's trace closed by his done that the work review has not read yet ('' when none); marked read."""
    try:
        proj = project(tp)
        if not proj:
            return ""
        def mark(rows):
            r = next((x for x in reversed(rows) if x.get("session") == tp and x.get("closed") and not x.get("reviewed")), None)
            if not r:
                return ""
            r["reviewed"] = True
            return render(r)
        if not any(r.get("session") == tp and r.get("closed") and not r.get("reviewed") for r in read(proj)):
            return ""
        return change(proj, mark)
    except Exception as e:
        ctx.log(f"tracing: closed trace not read: {e!r}")
        return ""
