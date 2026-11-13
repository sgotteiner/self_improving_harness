"""Transcript and slot helpers shared by the hooks. Transcript = jsonl; a human turn is a user entry with text."""
import json, os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SYSTEM_PREFIXES = ("<task-notification>", "[SYSTEM NOTIFICATION", "<system-reminder>", "<command-name>", "<local-command")


def enabled(slot):
    if slot == "capture" and os.environ.get("RECALL_CAPTURE") == "0":
        return False
    try:
        return bool(json.load(open(os.path.join(ROOT, "slots.json"), encoding="utf-8")).get(slot, {}).get("enabled"))
    except (OSError, ValueError):
        return False


def skip_env(var):
    """True when this process must stay silent: it is the brain itself, or the switch env var is 0."""
    return os.environ.get("RECALL_BRAIN") == "1" or os.environ.get(var) == "0"


def is_human(text):
    return bool(text) and not text.lstrip().startswith(SYSTEM_PREFIXES)


def entries(path):
    out = []
    try:
        for l in open(path, encoding="utf-8"):
            try:
                j = json.loads(l)
            except ValueError:
                continue
            if j.get("type") in ("user", "assistant") and isinstance(j.get("message"), dict) and not j.get("isSidechain"):
                out.append(j)
    except OSError:
        pass
    return out


def blocks(e):
    c = e["message"].get("content")
    return [{"type": "text", "text": c}] if isinstance(c, str) else (c or [])


def human_text(e):
    """Text of a real user message, else None (tool results and system notices are not human)."""
    if e["type"] != "user":
        return None
    t = "\n".join(b.get("text", "") for b in blocks(e) if b.get("type") == "text")
    return t if is_human(t) else None


def tool_line(b):
    inp = b.get("input", {})
    return f"{b.get('name')}: " + str(inp.get("command") or inp.get("file_path") or inp.get("pattern") or inp)[:150]


def _start(es, exclude):
    """Index after the last human message (ignoring one equal to `exclude`, the prompt being submitted now)."""
    return max([i for i, e in enumerate(es) if human_text(e) and human_text(e).strip() != exclude] or [-1]) + 1


def last_turn(path, exclude=None):
    """(assistant text, [tool call lines]) of the latest turn: everything after the last human message."""
    es = entries(path)
    start = _start(es, exclude)
    texts, tools = [], []
    for e in es[start:]:
        if e["type"] == "assistant":
            for b in blocks(e):
                if b.get("type") == "text":
                    texts.append(b["text"])
                elif b.get("type") == "tool_use":
                    tools.append(tool_line(b))
    return "\n".join(texts), tools


def recent(path, n=3, cap=500):
    """The last n human/assistant text turns as short lines, for situation description."""
    lines = []
    for e in entries(path):
        t = human_text(e) if e["type"] == "user" else "\n".join(b.get("text", "") for b in blocks(e) if b.get("type") == "text")
        if t and t.strip():
            lines.append(("Owner: " if e["type"] == "user" else "Assistant: ") + t.strip()[:cap])
    return lines[-n:]


def rejected_tool(path, exclude=None):
    """True if the latest turn contains a rejected/interrupted tool call (owner said no)."""
    es = entries(path)
    start = _start(es, exclude)
    return any("user doesn't want to proceed" in str(b.get("content", "")) or "interrupted by user" in str(b.get("content", "")).lower()
               for e in es[start:] for b in blocks(e) if b.get("type") == "tool_result")
