"""His verdict on a gate block, for cases/stats.json. When the gate blocks it stores the lessons as awaiting his verdict; his next
human message is judged by the message step's one model call (delegate.input_step), which answers VERDICT <id> RIGHT|WRONG|NONE.
RIGHT = right+1, WRONG = wrong+1, NONE or no answer = ignored+1; then the awaiting entries of that transcript are cleared."""
import json, os, re, time

import capstats, ctx, propread

AWAITING = os.path.join(ctx.ROOT, "scripts", "recall", "results", "gate_awaiting.json")
DAY = 86400  # an entry older than this is dropped unread
COUNT_KEY = {"RIGHT": "right", "WRONG": "wrong", "NONE": "ignored"}
VERDICT = re.compile(r"VERDICT\s+(\S+)\s+(RIGHT|WRONG|NONE)\b", re.I)
GATE_LINE = "End your fixed reply with one line: `gate: {cid} \u2014 <what it caught, a few words>`."
ASK = ("\n\nThe output gate blocked the assistant's previous reply on these lessons (id: what the gate said), and the assistant "
       "was to tell him in one `gate:` line:\n{items}\nOn the flags line also add, for each id, `VERDICT <id> RIGHT` (his message "
       "agrees it was a real mistake), `VERDICT <id> WRONG` (his message says it was a false alarm) or `VERDICT <id> NONE` "
       "(he says nothing clear about it). The `gate:` line in the assistant's reply and the gate's reason above are the assistant's "
       "and the gate's claims, not evidence. Answer RIGHT or WRONG only when HIS message contains words that agree or disagree "
       "with that block; anything else, including a bare \"ok\" or \"yes\" that answers a different question in the reply, is NONE.")


def _load():
    try:
        es = json.load(open(AWAITING, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    es = [e for e in es if isinstance(e, dict)]
    live = [e for e in es if time.time() - e.get("ts", 0) < DAY]
    for e in es:
        if e not in live:  # expired unread: counts as ignored, once (it is dropped from the file on the next save)
            try:
                capstats.bump(e["lesson"], "ignored")
                ctx.log(f"capverdict: awaiting {e.get('lesson')} expired unread, counted ignored")
            except Exception as ex:
                ctx.log(f"capverdict: expired count failed: {ex!r}")
    if len(live) != len(es):
        _save(live)  # so the dropped entries are not counted again by the next load
    return live


def _save(es):
    os.makedirs(os.path.dirname(AWAITING), exist_ok=True)
    json.dump(es, open(AWAITING, "w", encoding="utf-8"))


def add(tp, lesson, why):
    """The gate blocked tp on lesson: now awaiting his verdict (one entry per transcript and lesson)."""
    es = [e for e in _load() if not (e["tp"] == tp and e["lesson"] == lesson)]
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
    return ASK.format(items="\n".join(f"- {e['lesson']}: {e['why']}" for e in aw)) if aw else ""


def strip(out):
    """The reply without its VERDICT answers, so the kind and the flags are read as before."""
    return VERDICT.sub("", propread.strip(out))


def settle(tp, aw, out):
    """Count each awaiting lesson by the model's answer (none given = ignored; out "" when the call failed), then clear them."""
    said = {}
    for m in VERDICT.finditer(out):
        said.setdefault(m.group(1).strip("`*<>.,").lower(), m.group(2).upper())
    for e in aw:
        try:
            capstats.bump(e["lesson"], COUNT_KEY[said.get(e["lesson"].lower(), "NONE")])
        except Exception as ex:
            ctx.log(f"capverdict: count failed: {ex!r}")
    _save([e for e in _load() if e["tp"] != tp])


def ask(tp, text, tag, reply=""):
    """brain.ask(text + the awaiting lessons + the proposal he was shown) -> (reply without VERDICT and PROPOSAL answers, tokens);
    the answers are acted on here. reply = the assistant's last reply: a proposal counts as shown only if it has its line. If
    the call fails the verdicts count as ignored (logged), a proposal waits for his next message, and the error goes on."""
    import brain
    aw, pw = awaiting(tp), propread.waiting(tp, reply)
    try:
        out, tok = brain.ask(text + ask_text(aw) + propread.ask_text(pw), tag=tag)
    except Exception:
        ctx.log("capverdict: model call failed, awaiting verdicts count as ignored")
        settle(tp, aw, "")
        raise
    if aw:
        settle(tp, aw, out)
    propread.settle(pw, out)
    return strip(out), tok
