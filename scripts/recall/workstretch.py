"""The stretch of a session as the work review sends it to the brain: short lines (O / A / T / R), scrubbed with the privacy scan."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clean, ctx

STRETCH_MAX = 14000  # chars of the stretch sent to the brain: its tail
PART_MAX = 400  # chars kept of one message, call or result in the stretch


def stretch(tp, since=0, upto=None, es=None):
    """The work in entries since..upto as short lines (O / A / T / R), its last STRETCH_MAX chars. Each line goes through the privacy
    scan (clean.violations, strict): a tool result that fails is dropped, any other line that fails is kept as its tag and (redacted)."""
    cut_ = lambda t: " ".join(str(t).split())[:PART_MAX]
    out = []
    def add(tag, t):
        t = cut_(t)
        if clean.violations(t, strict=True):
            t = None if tag == "R" else "(redacted)"
        t is None or out.append(f"{tag}: {t}")
    for e in (ctx.entries(tp) if es is None else es)[since:upto]:
        for b in ctx.blocks(e):
            k = b.get("type")
            if k == "text" and e["type"] == "assistant":
                add("A", b["text"])
            elif k == "text" and ctx.human_text(e):
                add("O", b["text"])
            elif k == "tool_use":
                add("T", ctx.tool_line(b))
            elif k == "tool_result":
                c = b.get("content")
                add("R", " ".join(x.get("text", "") for x in c) if isinstance(c, list) else c)
    return "\n".join(out)[-STRETCH_MAX:]
