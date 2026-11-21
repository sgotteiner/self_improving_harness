"""His verdict on a gate block, for cases/stats.json. When the gate blocks it stores the lessons as awaiting his verdict; the
message step's one model call (delegate.input_step) sees every block still awaiting in the session and answers VERDICT <id> RIGHT|WRONG
for any his message judges. RIGHT = right+1, WRONG = wrong+1, then that entry is cleared; no verdict = it stays awaiting; an entry
older than DAY expires as ignored+1 (_load)."""
import json, os, re, time

import capstats, ctx, propread, situtrace

AWAITING = os.path.join(ctx.ROOT, "scripts", "recall", "results", "gate_awaiting.json")
DAY = 86400  # an entry older than this is dropped unread
COUNT_KEY = {"RIGHT": "right", "WRONG": "wrong"}  # NONE counts nothing: the block stays awaiting
VERDICT = re.compile(r"VERDICT\s+(\S+)\s+(RIGHT|WRONG|NONE)\b", re.I)
GATE_LINE = "End your fixed reply with one line: `gate: {cid} \u2014 <what it caught, a few words>`."
SHORT = 150  # the gate's reason as shown to the model
ASK = ("\n\nThe output gate blocked the assistant's replies earlier in this session on these lessons (id: what the gate said); each is "
       "still awaiting his verdict, and the assistant was to tell him in one `gate:` line:\n{items}\nOn the flags line also add, for each "
       "id his message gives a verdict on (any number of them, or none), `VERDICT <id> RIGHT` (his message agrees the block caught a real "
       "mistake, or praises that catch) or `VERDICT <id> WRONG` (his message says it was a false alarm). Add nothing for an id his message "
       "says nothing clear about: it stays awaiting. The `gate:` line in the assistant's reply and the gate's reason above are the "
       "assistant's and the gate's claims, not evidence. Answer only when HIS message contains words that agree or disagree with that "
       "block; a bare \"ok\" or \"yes\" that answers a different question in the reply is no verdict. Praise of a block above is its RIGHT "
       "verdict, not a PRAISE line: add a PRAISE line only for praise of anything else (other work of the setup), and none when his praise "
       "is only of the block.")


def _ignored(e, why):
    try:
        capstats.bump(e["lesson"], "ignored")
        ctx.log(f"capverdict: awaiting {e.get('lesson')} {why}, counted ignored")
    except Exception as ex:
        ctx.log(f"capverdict: ignored count failed: {ex!r}")


def _load():
    try:
        es = json.load(open(AWAITING, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    es = [e for e in es if isinstance(e, dict)]
    live = [e for e in es if time.time() - e.get("ts", 0) < DAY]
    for e in es:
        if e not in live:  # expired unread: counts as ignored, once (it is dropped from the file on the next save)
            _ignored(e, "expired unread")
    if len(live) != len(es):
        _save(live)  # so the dropped entries are not counted again by the next load
    return live


def _save(es):
    os.makedirs(os.path.dirname(AWAITING), exist_ok=True)
    json.dump(es, open(AWAITING, "w", encoding="utf-8"))


def add(tp, lesson, why):
    """The gate blocked tp on lesson: now awaiting his verdict (one entry per transcript and lesson)."""
    es = _load()
    for e in es:
        if e["tp"] == tp and e["lesson"] == lesson:  # an older one never got his verdict: ignored
            _ignored(e, "replaced unread")
    es = [e for e in es if not (e["tp"] == tp and e["lesson"] == lesson)]
    _save(es + [{"tp": tp, "lesson": lesson, "why": why, "ts": time.time()}])


def block(tp, lesson, why):
    """The gate's block text for one lesson (the `gate:` line to end the reply with); also stores it as awaiting. Fails open."""
    try:
        add(tp, lesson, why)
        return " " + GATE_LINE.format(cid=lesson)
    except Exception as e:
        ctx.log(f"capverdict: awaiting not stored: {e!r}")
        return ""


def awaiting(tp):
    return [e for e in _load() if e["tp"] == tp]


def ask_text(aw):
    """The text added to the message step's prompt ("" when nothing awaits)."""
    return ASK.format(items="\n".join(f"- {e['lesson']}: {e['why'][:SHORT]}" for e in aw)) if aw else ""


def strip(out):
    """The reply without its VERDICT answers, so the kind and the flags are read as before."""
    return VERDICT.sub("", propread.strip(out))


def settle(tp, aw, out):
    """Count each awaiting lesson the model gave RIGHT or WRONG on, and clear those entries; the others stay awaiting (until DAY)."""
    said = {}
    for m in VERDICT.finditer(out):
        said.setdefault(m.group(1).strip("`*<>.,").lower(), m.group(2).upper())
    done, rights = [], []
    for e in aw:
        try:
            verdict = said.get(e["lesson"].lower(), "NONE")
            if verdict == "NONE":
                continue
            capstats.bump(e["lesson"], COUNT_KEY[verdict])
            done.append(e["lesson"])
            if verdict == "RIGHT":  # the lesson fired: which situation was it (fails open); his praise of the catch is this verdict
                rights.append(e["lesson"])
                situtrace.fire(e["lesson"], e["why"])
        except Exception as ex:
            ctx.log(f"capverdict: count failed: {ex!r}")
    _save([e for e in _load() if not (e["tp"] == tp and e["lesson"] in done)])
    return rights


def ask(tp, text, tag, reply=""):
    """brain.ask(text + the awaiting lessons + the proposal he was shown) -> (reply without VERDICT and PROPOSAL answers, tokens);
    the answers are acted on here. reply = the assistant's last reply: a proposal counts as shown only if it has its line. If
    the call fails the blocks stay awaiting, a proposal is dropped, and the error goes on."""
    import brain
    aw, pw = awaiting(tp), propread.waiting(tp, reply)
    try:
        out, tok = brain.ask(text + ask_text(aw) + propread.ask_text(pw), tag=tag)
    except Exception:
        ctx.log("capverdict: model call failed, blocks stay awaiting, proposals dropped")
        propread.settle(pw, "")  # a proposal is never shown twice
        raise
    if aw:
        settle(tp, aw, out)
    propread.settle(pw, out)
    return strip(out), tok
