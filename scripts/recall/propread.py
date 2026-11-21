"""His answer to a proposal, read by the message step's one call (capverdict.ask adds the question). A proposal waits for it only
when the session's reply really had its `proposal <id>:` line (an offered one whose reply lacks it is offered once more, then dropped), and only
his next message in that same session (transcript) answers it. YES applies it, anything else drops it, a failed call too: a
proposal is never shown twice. Stdlib only."""
import datetime, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, proposals as pq

ASK = ("\n\nThe assistant was told to end its previous reply with this proposal line (id {pid}): `{text}`. On the flags "
       "line also add `PROPOSAL {pid} YES` only if HIS message clearly says yes to THAT proposal (a plain yes is enough when it is the only one). A yes to anything else in the "
       "reply (another question, a task, a fix to do) is not a yes to it, and neither is a bare \"ok\" or \"yes\" when the reply "
       "asked something else too; then add nothing.")
MANY = (" The reply carried several proposals: a yes counts only for the proposal ids his message names (one `PROPOSAL <id> YES` "
        "per id); a plain yes naming no id is a yes to none, add nothing.")
YES = re.compile(r"PROPOSAL\s+(?:(\S+)\s+)?YES\b", re.I)  # the id is missing in a plain yes


def _flat(s):
    return " ".join(s.lower().split())


def waiting(tp, reply, today=None):
    """The proposals of session tp that he was shown and has not answered. An offered one counts as shown only when `reply` (the
    assistant's last reply) has its `proposal <id>:` line; otherwise it goes back to the queue once (`again`: the hook offers it in the next reply),
    and the second time it is dropped."""
    today = today or str(datetime.date.today())
    lost = []

    def confirm(rows):
        for r in rows:
            if r["status"] == pq.OFFERED and r.get("tp") == tp:
                if _flat(f"proposal {r['pid']}: " + r["text"]) in _flat(reply):
                    r.update(status=pq.SHOWN, shown=today, at=time.time())
                elif r.get("again"):
                    r["status"] = pq.DROPPED
                    lost.append(dict(r))
                else:
                    r.update(status=pq.QUEUED, tp=None, again=True)
        return [dict(r) for r in rows if r["status"] == pq.SHOWN and r.get("tp") == tp]
    try:
        out = pq.change(confirm) if os.path.exists(pq.path()) else []
        for r in lost:  # its attached situations are retired, as for any drop
            try:
                __import__("propapply").drop(r)
            except Exception as e:
                ctx.log(f"proposals: situations of unshown {r['pid']} not retired: {e!r}")
        return out
    except Exception as e:
        ctx.log(f"proposals: queue unreadable: {e!r}")
        return []


def ask_text(rows):
    """The text added to the message step's prompt ("" when nothing waits)."""
    return "".join(ASK.format(pid=r["pid"], text=r["text"]) for r in rows) + (MANY if len(rows) > 1 else "")


def strip(out):
    """The reply without its PROPOSAL answers, so the kind and the flags are read as before."""
    return YES.sub("", out)


def settle(rows, out):
    """Apply each waiting proposal the model's answer says YES to, drop the rest. With several waiting a yes needs the
    proposal's id (a plain `PROPOSAL YES` applies none); with exactly one a plain yes applies it. A proposal that fails to apply is closed as
    failed and its attached situations are retired (never left proposed)."""
    import propapply
    found = list(YES.finditer(out))
    said = {m.group(1).strip("`*<>.,").lower() for m in found if m.group(1)}
    plain = len(rows) == 1 and any(not m.group(1) for m in found)
    for r in rows:
        yes = plain or r["pid"].lower() in said
        try:
            if yes:
                propapply.apply(r)
            else:
                propapply.drop(r)
            status = pq.APPLIED if yes else pq.DROPPED
        except Exception as e:
            ctx.log(f"proposals: {r['pid']} {r['kind']} failed: {e!r}")
            status = pq.FAILED
            try:
                if yes:
                    propapply.drop(r)
            except Exception as e2:
                ctx.log(f"proposals: situations of {r['pid']} not retired: {e2!r}")
        try:
            pq.change(lambda rs: [x.update(status=status, data=r["data"]) for x in rs if x["pid"] == r["pid"]])
        except Exception as e:
            ctx.log(f"proposals: status of {r['pid']} not stored: {e!r}")
