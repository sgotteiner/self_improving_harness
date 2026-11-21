"""Feature traces: one feature followed from the problem that led to it, through the work, to his done. A store of one file per
project, traces/<project>.jsonl (one line per trace {tid, project, title, why, opened, events, closed}), rewritten under the mdfile
lock. The message step's one call adds the line `TRACE <tid>` | `TRACE NEW | <title> | <why>` | `TRACE NONE` (ASK); tracechange.py
opens, attaches to and closes traces from it, and adds events found by code (traceevents.py). Event types: message, correction,
agent, commit, done, situation (an event may carry `sids`: the situations a capture write stored; a row may carry `from` {tid[, type,
event]}: the trace it started from; both only with the slot trace-links). Every function fails open: a trace never blocks a reply. Stdlib only (project detection loads diary lazily)."""
import datetime, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, mdfile, tracecount

DIR = os.path.join(ctx.ROOT, "traces")
TITLE_MAX, WHY_MAX, TEXT_MAX = 80, 300, 200  # chars kept of a title, a why quote, an event's text
RECORD_MAX = 1800  # chars of the trace in the one "record this trace" instruction (hook output is capped)
STALE_DAYS = 7  # an open trace with no event for this long is marked abandoned (kept, never deleted)
OPEN_LIST_MAX = 8  # open traces of the session listed in the message step's prompt
SEP, NEW, NONE = "|", "NEW", "NONE"  # the TRACE line: `TRACE NEW | title | why`, `TRACE NONE`
HUMANS_SHOWN, HUMAN_CUT = 10, 300  # his earlier messages shown for the why (the problem is often said many turns before the ask)
NO_WHY = "(not stated)"
ASK = ("\n\nOpen feature traces (a trace follows one feature from the problem that led to it up to his done):\n{open}\n\nHis earlier messages in this session, oldest first:\n{said}\n"
       "On the flags line also add exactly one line starting with TRACE: `TRACE <tid>` when his message is about one of the open "
       "traces (a follow-up, a correction or a done on it); `TRACE NEW | <title, 3 to 8 words> | <why>` when his message asks for, "
       "approves or settles on a new feature or change to build, in any kind (a task, or talk that agrees to add something the "
       "assistant or he raised), where <why> is ONE sentence naming the problem his ask responds to (not a restatement of the "
       "request, not a quote of the ask itself): build it from ALL his earlier messages and the assistant's previous reply above "
       "(his ask often reacts to what it just said, and he often states the problem many turns before), quoting his own words "
       "where they exist; `(not stated)` if there is no such problem; otherwise `TRACE NONE`. A question or a correction of "
       "the assistant is not a new feature: a correction about an open trace's feature is `TRACE <tid>`.")
LINE = re.compile(r"^\W*TRACE\s+(\S.*)$", re.M | re.I)
LINK_SLOT = "trace-links"  # the edges: trace -> situations it produced (sids on events), trace -> trace (`from`); off = no edge is added or asked for
FROM_CORRECTION, SITUATION = "correction", "situation"  # SITUATION: the event type that carries the sids of a write with no correction event
FROM_ASK = (" When you answer `TRACE NEW` and the new feature came out of one of the open traces above (for example from a correction "
            "the assistant got there, or a miss found while building it), add a last part: `TRACE NEW | <title> | <why> | FROM <tid>`, "
            "or `| FROM <tid> correction` when it came out of a correction in that trace. Leave the part off when the new feature did "
            "not come out of an open trace.")
FROM_PART = re.compile(r"FROM\s+(t\d+)(?:\s+(" + FROM_CORRECTION + r"))?", re.I)


def project(tp):
    """The project's name (its folder's), '' when the session's folder is in no project."""
    import diary, projcheck
    cwd = diary.project_of(tp)  # no cwd recorded: project_dir('') would answer with the hook's own folder
    d = projcheck.project_dir(cwd) if cwd else ""
    return re.sub(r"[^\w.-]+", "-", os.path.basename(d)).strip("-.").lower() if d else ""


def path(proj):
    return os.path.join(DIR, proj + ".jsonl")


def read(proj):
    try:
        return [json.loads(l) for l in mdfile.read(path(proj)).splitlines() if l.strip()]
    except (OSError, ValueError):
        return []


def change(proj, fn):
    """Let fn(rows) change the project's traces under the lock and write them back; returns fn's value."""
    os.makedirs(DIR, exist_ok=True)
    with mdfile.held(path(proj) + ".lock") as got:
        if not got:
            raise OSError("traces are locked")
        rows = read(proj)
        for r in rows:
            if not r.get("closed") and not r.get("abandoned") and not is_open(r):
                r["abandoned"] = str(datetime.date.today())
        out = fn(rows)
        mdfile.write_atomic(path(proj), "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        return out


def flat(s, n):
    return " ".join(str(s).split())[:n]


def add_event(row, session, typ, text, key=""):
    row["events"].append({"at": datetime.datetime.now().isoformat(timespec="seconds"), "type": typ, "text": flat(text, TEXT_MAX),
                          "session": session, **({"k": key} if key else {})})


def is_open(r):
    """Not closed, not abandoned, and with an event (or its opening) within STALE_DAYS."""
    if r.get("closed") or r.get("abandoned"):
        return False
    last = r["events"][-1]["at"] if r.get("events") else r["opened"]
    return datetime.datetime.now() - datetime.datetime.fromisoformat(last) <= datetime.timedelta(days=STALE_DAYS)


def mine(rows, tp):
    """The open traces of this session (transcript path), oldest first."""
    return [r for r in rows if r.get("session") == tp and is_open(r)]


def latest_open(rows, tp):
    return (mine(rows, tp) or [None])[-1]


def ask_text(tp, proj, prompt=""):
    """The text added to the message step's prompt ("" when the session is in no project or on failure); `proj` = project(tp),
    `prompt` = his new message, left out of his earlier ones when the transcript already holds it."""
    try:
        if not proj:
            return ""
        op = mine(read(proj), tp)[-OPEN_LIST_MAX:]
        said = [flat(t, HUMAN_CUT) for t in (ctx.human_text(e) for e in ctx.entries(tp)) if t and t.strip() != prompt.strip()]
        return ASK.format(open="\n".join(f"- {r['tid']}: {r['title']}" for r in op) or "(none)",
                          said="\n".join(f"- {t}" for t in said[-HUMANS_SHOWN:]) or "(none)") + (FROM_ASK if op and ctx.enabled(LINK_SLOT) else "")
    except Exception as e:
        ctx.log(f"tracing: ask text failed: {e!r}")
        return ""


def take(out):
    """(the reply without its TRACE lines, the text after the last TRACE or '')."""
    found = LINE.findall(out)
    return LINE.sub("", out), (found[-1].strip() if found else "")


def origin(rows, tp, part):
    """The `from` edge of a new trace from the TRACE NEW line's last part: {tid[, type, event]} when it is exactly `FROM <tid>
    [correction]` and the tid is an open trace of this session, else None. `event` = index of that trace's latest correction."""
    m = FROM_PART.fullmatch(part.strip(" `*."))
    if not m:
        return None
    src = next((x for x in mine(rows, tp) if x["tid"].lower() == m.group(1).lower()), None)
    if not src:
        return None
    i = next((i for i in reversed(range(len(src["events"]))) if src["events"][i]["type"] == FROM_CORRECTION), None) if m.group(2) else None
    return {"tid": src["tid"], **({"type": FROM_CORRECTION, "event": i} if i is not None else {})}


def render(r, cap=RECORD_MAX):
    f = r.get("from")  # rows from before the edges have neither `from` nor event sids
    head = (f"Feature trace {r['tid']}: {r['title']}\nWhy: {r['why']}\nOpened {r['opened']}" + (f", closed {r['closed']}" if r.get("closed") else "")
            + (f"\nStarted from {f['tid']}" + (f" ({f['type']} event {f['event']})" if "event" in f else "") if f else ""))
    try:
        iv = tracecount.line(*tracecount.counts(r, read(r.get("project", ""))))
    except Exception:
        iv = ""
    head += "\n" + iv if iv else ""
    return (head + "".join(f"\n- {e['at'][:10]} {e['type']}: {e['text']}" + (f" [{', '.join(e['sids'])}]" if e.get("sids") else "")
                           for e in r["events"]))[:cap]


if __name__ == "__main__" and sys.argv[1:2] == ["interventions"]:
    print(tracecount.report(*sys.argv[2:3]))
