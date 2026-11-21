"""The model's own 1-5 "how sure am I" for a lesson match, shared by the output gate (gate.py) and the message step
(delegate.input_step). Not ctx.RELEVANCE_MIN: that one is the embedding cosine cutoff. Stdlib only."""
import re

import ctx

RELEVANCE_MIN = 4  # at this score or above a lesson blocks (gate) or a correction / praise is captured (message step)
_SCORE = re.compile(r"\s*\W?([1-5])\W?\s*(?:/\s*5\s*)?\|\s*(.*)", re.S)


def split(text):
    """'<score> | <rest>' -> (score 1-5, rest). A missing or malformed score -> (None, text unchanged). The callers decide what None
    means: the gate does not block, the message step still captures, so a parse failure never loses his correction."""
    m = _SCORE.fullmatch(text)
    return (int(m.group(1)), m.group(2).strip()) if m else (None, text)


def judge(text):
    """-> (sure, score, sentence) for a message-step guess. sure is False only for a well-formed score below the minimum; a score
    that is missing or malformed counts as sure (the capture line, as before), so a parse failure never loses his correction."""
    score, why = split(text)
    return score is None or score >= RELEVANCE_MIN, score, why or "not specified"


def sort(texts, prompt=""):
    """-> ([each guess's sentence if he surely meant it, else ""], the first weak guess (score, sentence) or None). "" stays "".
    Every weak guess is logged with his message, so a dropped correction or praise can be found and audited later."""
    out, weak = [], None
    for t in texts:
        ok, score, why = judge(t) if t else (False, 0, "")
        out.append(why if ok else "")
        if t and not ok:
            ctx.log(f"relevance: dropped below {RELEVANCE_MIN} ({score}/5): {why[:200]!r} | his message: {prompt[:200]!r}")
            weak = weak or (score, why)
    return out, weak
