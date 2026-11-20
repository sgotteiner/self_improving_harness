"""Test-guard hook (slot `test-guard` in slots.json): no test file is created or edited without the owner's approval
(his rule: a test only for what failed, may fail or he asked; proposed in one line, made after his yes).

  pre    (PreToolUse on Write|Edit|MultiEdit|NotebookEdit and Bash): a write into a path matching the slot's `pattern` is
         blocked (exit 2 + message) unless an approval for this session is still valid. Bash: redirects, tee, cp, mv.
  prompt (UserPromptSubmit): his short yes, when the assistant's previous reply ended with the `check: ... yes / ignore`
         line, records an approval for the session for `minutes`. Only his own message can grant it. Anything else = no.

Fails open on its own errors (logged to state/test-guard.log); a matching path without approval blocks."""
import json, os, re, sys, time

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state")
APPROVED_FILE = os.path.join(STATE, "test-guard-ok")   # lines: "<session_id> <epoch>"
LOG = os.path.join(STATE, "test-guard.log")
YES = re.compile(r"^\s*(y|yes|yeah|yep|ok|okay|sure|go|go on|go ahead|do it|proceed)\b[\s.!]*$", re.I)
ASKED = re.compile(r"check:.*(prevents|—|-).*yes\s*/\s*ignore", re.I | re.S)
FILE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
BASH_TARGETS = [re.compile(r"(?<![<>&\d])\d?>>?\s*(?!&)([^\s;|&<>]+)"), re.compile(r"\btee\s+(?:-\w+\s+)*([^\s;|&<>]+)"),
                re.compile(r"\b(?:cp|mv)\s+(?:-\w+\s+)*(?:\S+\s+)+?([^\s;|&<>]+)\s*(?:[;|&\n]|$)")]
BLOCK_MSG = ("TEST GUARD: writing a test file ({path}) needs the owner's approval, and he has not given it. Do not write it "
             "and do not get around this (another tool, another path). Propose it to him in one line ending exactly with "
             "`check: <what it checks> — prevents <failure> — yes / ignore`, then stop and wait for his answer.")


def _slot():
    return json.load(open(os.path.join(ROOT, "slots.json"), encoding="utf-8")).get("test-guard", {})


def _log(msg):
    try:
        os.makedirs(STATE, exist_ok=True)
        open(LOG, "a", encoding="utf-8").write(f"{time.strftime('%F %T')} {msg}\n")
    except OSError:
        pass


def targets(event):
    """The paths this tool call writes to."""
    inp = event.get("tool_input") or {}
    if event.get("tool_name") in FILE_TOOLS:
        return [inp.get("file_path") or inp.get("notebook_path") or ""]
    cmd = inp.get("command", "") if event.get("tool_name") == "Bash" else ""
    return [m.group(1).strip("'\"") for rx in BASH_TARGETS for m in rx.finditer(cmd)]


def approved(session, minutes):
    try:
        lines = open(APPROVED_FILE, encoding="utf-8").read().splitlines()
    except OSError:
        return False
    return any(l.split()[0] == session and time.time() - float(l.split()[1]) <= minutes * 60 for l in lines if len(l.split()) == 2)


def pre(event, slot):
    """The block message, or None to let the call through."""
    if not slot.get("enabled"):
        return None
    rx = re.compile(slot["pattern"])
    for t in targets(event):
        p = t.replace("\\", "/")
        if p and rx.search(p) and not approved(event.get("session_id", ""), int(slot["minutes"])):
            return BLOCK_MSG.format(path=p)
    return None


def _asked(path):
    """True when the assistant's last text reply carries the `check: ... yes / ignore` proposal line."""
    try:
        es = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    except (OSError, ValueError):
        return False
    for e in reversed(es):
        c = (e.get("message") or {}).get("content")
        if e.get("type") == "assistant" and isinstance(c, list):
            t = "\n".join(b.get("text", "") for b in c if b.get("type") == "text").strip()
            if t:
                return bool(ASKED.search(t))
    return False


def prompt(event, slot):
    """His yes to the proposal line -> approval for this session. Returns the line to show, or None."""
    if not slot.get("enabled") or not YES.match(event.get("prompt", "")) or not _asked(event.get("transcript_path", "")):
        return None
    os.makedirs(STATE, exist_ok=True)
    with open(APPROVED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{event.get('session_id', '')} {time.time()}\n")
    return f"test-guard: he approved the check; test files may be written for {slot['minutes']} min in this session."


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre"
    try:
        event, slot = json.load(sys.stdin), _slot()
        out = (prompt if mode == "prompt" else pre)(event, slot)
    except Exception as e:
        _log(f"{mode}: {e!r}")
        return
    if out and mode == "prompt":
        print(out)
    elif out:
        print(out, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
