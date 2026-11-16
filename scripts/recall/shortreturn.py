"""Short agent returns (switch `short-returns` in slots.json). A SubagentStop hook measures the agent's final message: over
MAX_LINES lines -> block once, telling it to return a short summary. Never blocks twice (stop_hook_active). Fails open: a
missing message, a missing switch or any error means the agent stops as it is. The message comes from the payload's
`last_assistant_message`, else from the last assistant text of `agent_transcript_path`."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx

MAX_LINES = 25
REASON = ("Return a short summary only (what was done, errors, important notes, your own choices in one line), "
          f"under {MAX_LINES} lines.")


def last_message(d):
    m = d.get("last_assistant_message")
    if isinstance(m, str) and m.strip():
        return m
    try:
        text = ""
        for l in open(d.get("agent_transcript_path", ""), encoding="utf-8"):
            e = json.loads(l)
            if e.get("type") == "assistant":
                t = "\n".join(b.get("text", "") for b in e["message"]["content"] if isinstance(b, dict) and b.get("type") == "text")
                if t.strip():
                    text = t
        return text
    except Exception:
        return ""


def verdict(d):
    """The block JSON for this SubagentStop payload, or '' to let the agent stop."""
    if not ctx.enabled("short-returns") or d.get("stop_hook_active"):
        return ""
    if len(last_message(d).strip().splitlines()) <= MAX_LINES:
        return ""
    return json.dumps({"decision": "block", "reason": REASON})


if __name__ == "__main__":
    try:
        o = verdict(json.load(sys.stdin))
        if o:
            print(o, flush=True)
    except Exception as e:
        ctx.log(f"shortreturn: failed open: {e!r}")
    sys.exit(0)
