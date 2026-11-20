"""The one proposal queue: cases/_pending/proposals.jsonl (local, never pushed), one line per proposal to change the knowledge
(kinds in propapply.py). One a day at most, and one outstanding at a time. The hook offers it (line) as one line the session ends
its reply with (`proposal: <text> -- yes / ignore`, the way the gate's `gate:` line works); it counts as shown only when that
reply has the line, and his next message in that session is judged by the message step's one call (propread.py): YES applies it,
anything else drops it. Nothing is deleted: a line only changes status (queued, offered, shown, applied, dropped, failed).
Every function fails open: a broken queue never stops a hook. Stdlib only."""
import datetime, json, os, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, index, mdfile

QUEUE_FILE = "proposals.jsonl"
QUEUED, OFFERED, SHOWN, APPLIED, DROPPED, FAILED = "queued", "offered", "shown", "applied", "dropped", "failed"
OPEN = (OFFERED, SHOWN)  # at most one line is in these at a time
DAY = 86400  # an offer nobody answered goes back to the queue, a shown one nobody answered is dropped (no answer = no)
PID_FORMAT = "p%04d"
OFF_MARK = os.path.join(tempfile.gettempdir(), "recall-proposals-off")  # the day the "proposals are off" note was logged
LINE = "End your reply with this one line, as written: `proposal: {text} — yes / ignore`."


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
    """Add a proposal (kind: see propapply.KINDS); returns its pid, or None when the same one is already open."""
    def add(rows):
        if any(r["kind"] == kind and r["data"] == data and r["status"] in (QUEUED,) + OPEN for r in rows):
            return None
        rows.append({"pid": PID_FORMAT % (len(rows) + 1), "kind": kind, "text": " ".join(text.split()), "data": data,
                     "status": QUEUED, "created": str(datetime.date.today()), "shown": None, "tp": None, "at": 0})
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
    now = time.time()
    for r in rows:
        if r["status"] in OPEN and now - r.get("at", 0) > DAY:
            if r["status"] == OFFERED:
                r.update(status=QUEUED, tp=None)
            else:
                r["status"] = DROPPED
                try:
                    __import__("propapply").drop(r)
                except Exception as e:
                    ctx.log(f"proposals: situations of unanswered {r['pid']} not retired: {e!r}")


def line(tp, today=None):
    """The instruction for the session (transcript tp) to end its reply with the next queued proposal; "" if none, one is
    outstanding, or one was shown today. The proposal is only offered: propread.waiting marks it shown once the reply has it."""
    try:
        today = today or str(datetime.date.today())

        def pick(rows):
            _expire(rows)
            r = next((r for r in rows if r["status"] == QUEUED), None)
            if not r or any(x["status"] in OPEN or x["shown"] == today for x in rows) or not readable(today):
                return ""
            r.update(status=OFFERED, tp=tp, at=time.time())
            return LINE.format(text=r["text"])
        return change(pick) if os.path.exists(path()) else ""
    except Exception as e:
        ctx.log(f"proposals: line failed: {e!r}")
        return ""
