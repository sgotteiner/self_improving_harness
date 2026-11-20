"""Events of an open feature trace found by code at the Stop hook, no model call: an agent that returned this turn (its type and the
start of its result) and a git commit (hash and subject, from the commit's own tool output). Text taken from tool output goes
through the privacy scan (clean.violations, strict) and is replaced by "(redacted)" when it fails. gate.py calls at_stop(); fails open."""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clean, ctx, tracechange, tracing

KEY_CUT = 80  # chars of an agent's first result line in its dedupe key
RESULT = re.compile(r"<result>(.*?)</result>", re.S)
COMMIT = re.compile(r"\[[^\]]*\s([0-9a-f]{7,40})\]\s+(.*?)(?=\s+\d+ files? changed|\s+create mode|$)")  # `git commit` output, flattened


def _safe(text):
    t = " ".join(text.split())[:tracing.TEXT_MAX]
    return "(redacted)" if clean.violations(t, strict=True) else t


def events(t):
    """[(key, type, text)] from the facts of the turn (turnfacts.turn)."""
    out = []
    for kind, res in t.get("rets", []):
        m = RESULT.search(res)
        first = next((l for l in (m.group(1) if m else res).splitlines() if l.strip()), "").strip()
        out.append((f"agent|{kind}|{first[:KEY_CUT]}", "agent", f"{kind}: {_safe(first)}"))
    for res in t.get("commits", []):
        m = COMMIT.search(res)
        if m:
            out.append((f"commit|{m.group(1)}", "commit", f"{m.group(1)[:8]} {_safe(m.group(2))}"))
    return out


def at_stop(tp):
    """Add this turn's agent returns and commits to this session's open trace, if it has one. Never raises."""
    try:
        proj = tracing.project(tp)
        if not proj or not tracing.mine(tracing.read(proj), tp):
            return
        import turnfacts
        tracechange.add_events(tp, proj, events(turnfacts.turn(tp)))
    except Exception as e:
        ctx.log(f"traceevents: failed: {e!r}")
