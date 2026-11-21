"""The one proposal queue: cases/_pending/proposals.jsonl (local, never pushed), one line per proposal to change the knowledge
(kinds in propapply.py). No limit and no waiting: a proposal is shown in the very next reply, all of them in one, one line each
(offer: a capture write ends its own reply with it; line: the hook attaches those a background producer queued). The session ends
its reply with `proposal <id>: <text> -- yes / no`; it counts as shown only when that reply has the line, and his next message in
that session is judged by the message step's one call (propread.py): YES applies it, anything else drops it, for good (a proposal
whose reply lacked its line is offered once more). A dropped or failed change is not queued again (queue, propkey). Nothing is deleted: a line only changes status (queued, offered, shown, applied, dropped,
failed). Every function fails open: a broken queue never stops a hook. Stdlib only."""
import datetime, json, os, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, index, mdfile, propkey

QUEUE_FILE = "proposals.jsonl"
QUEUED, OFFERED, SHOWN, APPLIED, DROPPED, FAILED = "queued", "offered", "shown", "applied", "dropped", "failed"
OPEN = (OFFERED, SHOWN)  # told to the session / waiting for his next message
DAY = propkey.DAY  # an open proposal nobody answered in this time is dropped (no answer = no)
PID_FORMAT = "p%04d"
OFF_MARK = os.path.join(tempfile.gettempdir(), "recall-proposals-off")  # the day the "proposals are off" note was logged
LINE = "End your reply with this one line, as written: `proposal {pid}: {text} -- yes / no`."


def path():
    return os.path.join(index.CASES, "_pending", QUEUE_FILE)


def read():
    try:
        return [json.loads(l) for l in mdfile.read(path()).splitlines() if l.strip()]
    except FileNotFoundError:
        return []


def change(fn):
    """Read the queue, let fn(rows) change it (return value is passed on), write it back, all under the queue's lock."""
    os.makedirs(os.path.dirname(path()), exist_ok=True)
    with mdfile.held(path() + ".lock") as got:
        if not got:
            raise OSError("proposal queue is locked")
        rows = read()
        out = fn(rows)
        mdfile.write_atomic(path(), "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        return out


def queue(kind, text, data):
    """Add a proposal (kind: see propapply.KINDS); returns its pid, or None when the same change is already open, or was dropped
    or failed (propkey: for good, or for DROP_DAYS unless a new real occurrence is attached; logged)."""
    def add(rows):
        for r in rows:
            if propkey.key(r["kind"], r["data"]) != propkey.key(kind, data):
                continue
            if r["status"] in (QUEUED,) + OPEN:
                return None
            if r["status"] in (DROPPED, FAILED) and propkey.blocks(r, kind, data, time.time()):
                ctx.log(f"proposals: skipped, {r['pid']} with the same change was {r['status']}: {text[:100]}")
                return None
        rows.append({"pid": PID_FORMAT % (len(rows) + 1), "kind": kind, "text": " ".join(text.split()), "data": data,
                     "status": QUEUED, "created": str(datetime.date.today()), "shown": None, "tp": None, "at": 0,
                     "sits": propkey.sits()})
        return rows[-1]["pid"]
    return change(add)


def readable(today):
    """His yes is read by the message step's call (slot delegation-hook) and proposals belong to capture. When either is off a
    proposal could not be answered: none is shown (logged once a day)."""
    if ctx.enabled("delegation-hook") and ctx.enabled("capture"):
        return True
    try:
        if not os.path.exists(OFF_MARK) or mdfile.read(OFF_MARK) != today:
            mdfile.write_atomic(OFF_MARK, today)
            ctx.log("proposals: not shown, delegation-hook or capture is off so his answer could not be read")
    except OSError:
        pass
    return False


def _expire(rows):
    """An offered or shown proposal nobody answered for a day is dropped, never shown again (no answer = no)."""
    now = time.time()
    for r in rows:
        if r["status"] in OPEN and now - r.get("at", 0) > DAY:
            r["status"] = DROPPED
            try:
                __import__("propapply").drop(r)
            except Exception as e:
                ctx.log(f"proposals: situations of unanswered {r['pid']} not retired: {e!r}")


def _offer(r, tp):
    r.update(status=OFFERED, tp=tp, at=time.time())
    return LINE.format(pid=r["pid"], text=r["text"])


def offer(pid, tp):
    """The instruction for the session (transcript tp) to end this very reply with proposal pid (a capture write just made it);
    "" when it cannot be answered (no session, or the steps that read his yes are off): the hook's line then attaches it."""
    try:
        ok = bool(pid and tp) and readable(str(datetime.date.today()))

        def pick(rows):
            r = next((r for r in rows if r["pid"] == pid and r["status"] == QUEUED), None)
            return _offer(r, tp) if r and ok else ""
        return change(pick)
    except Exception as e:
        ctx.log(f"proposals: offer failed: {e!r}")
        return ""


def line(tp, today=None):
    """The instructions for the session (transcript tp) to end its reply with every queued proposal, one line each: [] if none.
    The proposals are only offered: propread.waiting marks each shown once the reply has its line, and drops it otherwise."""
    try:
        today = today or str(datetime.date.today())

        def pick(rows):
            _expire(rows)
            queued = [r for r in rows if r["status"] == QUEUED]
            return [_offer(r, tp) for r in queued] if queued and readable(today) else []
        return change(pick) if os.path.exists(path()) else []
    except Exception as e:
        ctx.log(f"proposals: line failed: {e!r}")
        return []
