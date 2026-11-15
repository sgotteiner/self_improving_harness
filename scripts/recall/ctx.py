"""Transcript and slot helpers shared by the hooks. Transcript = jsonl; a human turn is a user entry with text."""
import datetime, json, os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SYSTEM_PREFIXES = ("<task-notification>", "[SYSTEM NOTIFICATION", "<system-reminder>", "<command-name>", "<local-command",
                   "[Request interrupted by user", "Base directory for this skill", "Stop hook feedback")
# A background agent's result wakes the session without a human message. For the gate it starts a new turn, and its
# text is evidence of what was done (e.g. "agent returned, files committed"), so it is handed over with the tool calls.
NOTICE_PREFIX = "<task-notification>"
LOG = os.path.join(ROOT, "scripts", "recall", "results", "hook.log")
# Relevance cutoff on cosine (fastembed bge-small), shared by hook.py and gate.py. Below it a case is
# not worth a brain call. Set from `python -I scripts/recall/eval_recall.py` (it prints the chosen value): the lowest
# 0.01 step where at most 1 of 22 unrelated eval queries passes, keeping 28/30 recall. Unrelated text tops out at 0.62
# median / 0.74 max on this model, so the old 0.60 passed nearly all.
RELEVANCE_MIN = 0.70


def log(msg):
    """One line to the gitignored results/hook.log, so a silent exit can be explained later."""
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
    except OSError:
        pass


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


def chunks(text, width=800):
    """One chunk per non-empty line (long lines cut every `width` chars) so the embedder, which reads ~512 tokens, sees
    all of the text, and a short claim at the end is not diluted by what came before. A case scores by its best chunk."""
    return [l[i:i + width] for l in text.splitlines() if l.strip() for i in range(0, len(l), width)]


def tool_line(b):
    inp = b.get("input", {})
    return f"{b.get('name')}: " + str(inp.get("command") or inp.get("file_path") or inp.get("pattern") or inp)


def _start(es, exclude):
    """Index after the last human message (ignoring one equal to `exclude`, the prompt being submitted now)."""
    return max([i for i, e in enumerate(es) if human_text(e) and human_text(e).strip() != exclude] or [-1]) + 1


def _notice(e):
    """Text of a background-agent notification entry, else None."""
    if e["type"] != "user":
        return None
    t = "\n".join(b.get("text", "") for b in blocks(e) if b.get("type") == "text")
    return t if t.lstrip().startswith(NOTICE_PREFIX) else None


def last_turn(path, exclude=None):
    """(assistant text, [tool call lines]) of the latest turn: everything after the last human message or, if later,
    the last background-agent notification (whose text is included as evidence)."""
    es = entries(path)
    start = _start(es, exclude)
    texts, tools = [], []
    notices = [i for i, e in enumerate(es) if i >= start and _notice(e)]
    if notices:
        start = notices[-1] + 1
        tools.append("Background agent result received this turn:\n" + (_notice(es[notices[-1]]) or ""))
    for e in es[start:]:
        if e["type"] == "assistant":
            for b in blocks(e):
                if b.get("type") == "text":
                    texts.append(b["text"])
                elif b.get("type") == "tool_use":
                    tools.append(tool_line(b))
    return "\n".join(texts), tools


def recent(path, n=3):
    """The last n human/assistant text turns as short lines, for situation description."""
    lines = []
    for e in entries(path):
        t = human_text(e) if e["type"] == "user" else "\n".join(b.get("text", "") for b in blocks(e) if b.get("type") == "text")
        if t and t.strip():
            lines.append(("Owner: " if e["type"] == "user" else "Assistant: ") + t.strip())
    return lines[-n:]


def rejected_tool(path, exclude=None):
    """True if the latest turn contains a rejected/interrupted tool call (owner said no)."""
    es = entries(path)
    start = _start(es, exclude)
    return any("user doesn't want to proceed" in str(b.get("content", "")) or "interrupted by user" in str(b.get("content", "")).lower()
               for e in es[start:] for b in blocks(e) if b.get("type") == "tool_result")
