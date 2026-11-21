"""The review loop, forced by code (Stop hook, called by gate.py; no model call): the reviewer's latest result of this turn says
"Complete: no" and "needs his judgment: no", no implementer call came after it, fewer than LOOP_MAX rework rounds (implementer calls
after the first build) were made since his last message, and the loop has blocked fewer than LOOP_MAX times since it (counted in
results/review_loop.json, so a session that ignores the block is let go too) -> block the stop and send the missing parts to the
implementer. Needs his judgment, or a limit reached: no block, the reply brings it to him. Slot `review-loop`. Fails open (any
error: no block). Stdlib only."""
import json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, mdfile, transcript

SLOT = "review-loop"
LOOP_MAX = 3  # rework rounds (implementer calls after the first build) and loop blocks since his last message
STATE = os.path.join(ctx.ROOT, "scripts", "recall", "results", "review_loop.json")  # {transcript: [index of his last message, blocks, time]}
DAY = 86400  # a transcript's counter older than this is dropped on the next write, as capverdict drops its entries
MISSING_MAX = 700  # chars of the reviewer's list passed on
INCOMPLETE = re.compile(r"Complete:\s*no\b", re.I)
JUDGMENT = re.compile(r"needs his judgment:\s*(yes|no)\b", re.I)
REASON = ("The reviewer says the work is incomplete and needs no judgment of his: send the missing parts to the implementer now "
          "(rework round {n} of {max}), with the reviewer's list: {list}")


def _is(kind, name):
    return name in str(kind)


def _state():
    return os.environ.get("RECALL_LOOP_STATE") or STATE  # the checks point it at a scratch file


def blocks(tp, start, add=False):
    """Loop blocks counted for this transcript since his message number `start`; add=True counts one more."""
    try:
        s = json.loads(mdfile.read(_state()))
    except (OSError, ValueError):
        s = {}
    n = s[tp][1] if s.get(tp, [None])[0] == start and time.time() - s[tp][2] < DAY else 0
    if add:
        s = {k: v for k, v in s.items() if time.time() - v[2] < DAY}
        s[tp] = [start, n + 1, time.time()]
        os.makedirs(os.path.dirname(_state()), exist_ok=True)
        mdfile.write_atomic(_state(), json.dumps(s))
    return n


def reason(tp):
    """The block reason, or None."""
    try:
        if not ctx.enabled(SLOT):
            return None
        es = ctx.entries(tp)
        last = max([i for i, e in enumerate(es) if ctx.human_text(e)] or [-1])  # his last message
        start = (last + 1) * transcript.SEQ
        cs, ns = transcript.calls(es), transcript.notices(es)
        types = transcript.agent_types(cs, ns)
        def kind(c):  # the agent type an Agent call starts or a SendMessage resumes
            return types.get(str(c["input"].get("to", "")), "") if c["name"] == "SendMessage" else str(c["input"].get("subagent_type", ""))
        agents = [(c["seq"], kind(c), c["result"]) for c in cs if c["name"] in ("Agent", "Task", "SendMessage") and c["seq"] >= start]
        for s, t in ns:  # a background reviewer's result comes as a notification
            m, tid = transcript.TASK_ID.search(t), transcript.TOOL_ID.search(t)
            agents.append((s, types.get(tid.group(1) if tid else "") or types.get(m.group(1) if m else "") or "", t))
        agents = sorted(a for a in agents if a[0] >= start)
        done = [a for a in agents if _is(a[1], "reviewer") and INCOMPLETE.search(a[2])]
        if not done:
            return None
        seq, _, text = done[-1]
        j = JUDGMENT.search(text, INCOMPLETE.search(text).end())
        if not j or j.group(1).lower() != "no":
            return None  # his judgment is needed (or the reviewer did not say): the reply brings it to him
        if any(a[0] > seq and (_is(a[1], "implementer") or _is(a[1], "reviewer")) for a in agents):
            return None  # the missing parts already went out, or a new review is under way
        rework = max(sum(1 for a in agents if _is(a[1], "implementer")) - 1, 0)  # the first build is no rework
        sent = blocks(tp, last)
        if rework >= LOOP_MAX or sent >= LOOP_MAX:
            return None
        blocks(tp, last, add=True)
        ctx.log(f"reviewloop: block {sent + 1} of {LOOP_MAX} (rework rounds so far {rework})")
        return REASON.format(n=rework + 1, max=LOOP_MAX, list=text[INCOMPLETE.search(text).start():j.start()].strip()[:MISSING_MAX])
    except Exception as e:
        ctx.log(f"reviewloop: failed: {e!r}")
        return None
