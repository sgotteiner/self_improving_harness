"""His answer to a proposal, read by the message step's one call (capverdict.ask adds the question). A proposal waits for it only
when the session's reply really had its `proposal:` line (an offered one whose reply lacks it goes back to the queue), and only
his next message in that same session (transcript) answers it. YES applies it, anything else drops it; a failed call settles
nothing (it waits for the next message). Stdlib only."""
import datetime, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, proposals as pq

ASK = ("\n\nThe assistant was told to end its previous reply with this proposal line (id {pid}): `proposal: {text}`. On the flags "
       "line also add `PROPOSAL {pid} YES` only if HIS message clearly says yes to THAT proposal. A yes to anything else in the "
       "reply (another question, a task, a fix to do) is not a yes to it, and neither is a bare \"ok\" or \"yes\" when the reply "
       "asked something else too; then add nothing.")
YES = re.compile(r"PROPOSAL\s+(\S+)\s+YES\b", re.I)


def _flat(s):
    return " ".join(s.lower().split())


def waiting(tp, reply, today=None):
    """The proposals of session tp that he was shown and has not answered. An offered one counts as shown only when `reply` (the
    assistant's last reply) has its `proposal:` line; otherwise it goes back to the queue, not dropped."""
    today = today or str(datetime.date.today())

    def confirm(rows):
        for r in rows:
            if r["status"] == pq.OFFERED and r.get("tp") == tp:
                if _flat("proposal: " + r["text"]) in _flat(reply):
                    r.update(status=pq.SHOWN, shown=today, at=time.time())
                else:
                    r.update(status=pq.QUEUED, tp=None)
        return [dict(r) for r in rows if r["status"] == pq.SHOWN and r.get("tp") == tp]
    try:
        return pq.change(confirm) if os.path.exists(pq.path()) else []
    except Exception as e:
        ctx.log(f"proposals: queue unreadable: {e!r}")
        return []


def ask_text(rows):
    """The text added to the message step's prompt ("" when nothing waits)."""
    return "".join(ASK.format(pid=r["pid"], text=r["text"]) for r in rows)


def strip(out):
    """The reply without its PROPOSAL answers, so the kind and the flags are read as before."""
    return YES.sub("", out)


def settle(rows, out):
    """Apply each waiting proposal the model's answer says YES to, drop the rest. A proposal that fails to apply is closed as
    failed and its attached situations are retired (never left proposed)."""
    import propapply
    said = {m.group(1).strip("`*<>.,").lower() for m in YES.finditer(out)}
    for r in rows:
        yes = r["pid"].lower() in said
        try:
            propapply.apply(r) if yes else propapply.drop(r)
            status = pq.APPLIED if yes else pq.DROPPED
        except Exception as e:
            ctx.log(f"proposals: {r['pid']} {r['kind']} failed: {e!r}")
            status = pq.FAILED
            try:
                yes and propapply.drop(r)
            except Exception as e2:
                ctx.log(f"proposals: situations of {r['pid']} not retired: {e2!r}")
        try:
            pq.change(lambda rs: [x.update(status=status) for x in rs if x["pid"] == r["pid"]])
        except Exception as e:
            ctx.log(f"proposals: status of {r['pid']} not stored: {e!r}")
