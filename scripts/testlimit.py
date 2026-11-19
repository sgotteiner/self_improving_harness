"""Test-limit hook (slot `test-limit` in slots.json): a test or eval run gets at most `seconds`, then the agent stops and
asks the owner whether to continue (his rule, 2026-11-16).

  pre  (PreToolUse on Bash): a command that RUNS a test (a command segment matching `pattern`) is wrapped in GNU
       `timeout`. When it is cut, the wrapper records the command in state/test-limit-stopped and prints STOPPED.
  prompt (UserPromptSubmit): his short yes ("continue", "yes", "go on", ...) while a cut run is recorded writes
       state/test-limit-ok for that exact command, valid APPROVAL_MIN minutes, used once. Only his own message can
       grant it: an agent never triggers UserPromptSubmit, and an approval only matches the command that was cut.

Fails open: any error -> the command runs unchanged. Known limit: a `cd`/`export` inside a wrapped command does not carry
to the next call (it runs in a child shell)."""
import base64, hashlib, json, os, re, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLOTS = os.path.join(ROOT, "slots.json")
STATE = os.path.join(ROOT, "state")
STOPPED_FILE = os.path.join(STATE, "test-limit-stopped")
APPROVED_FILE = os.path.join(STATE, "test-limit-ok")
APPROVAL_MIN = 30          # an approval is valid this long after his yes
KILL_GRACE_S = 5           # after the limit, `timeout` sends KILL this many seconds after TERM
MAX_WRAP_CHARS = 20000     # longer commands are left unwrapped (Windows command-line length)
SEGMENT = re.compile(r"&&|\|\||[;|\n]")
YES = re.compile(r"^\s*(y|yes|yeah|yep|ok|okay|sure|go|go on|go ahead|continue|keep going|run it|do it|proceed)\b[\s.!]*$",
                 re.I)
STOP_MSG = ("TEST STOPPED after {n} s by the test-limit hook. Stop here: tell the owner in plain words what this run "
            "checks and how far it got, and ask whether to continue. Do not re-run, split or shorten it to get around the limit.")


def _slot():
    return json.load(open(SLOTS, encoding="utf-8")).get("test-limit", {})


def _hash(cmd):
    return hashlib.sha256(cmd.strip().encode("utf-8")).hexdigest()


def runs_test(cmd, pattern):
    """True when a segment of the command starts by running a test (so `git commit -m "fix test_x.py"` is not one)."""
    rx = re.compile(pattern)
    return any(rx.match(s.strip()) for s in SEGMENT.split(cmd) if s.strip())


def wrap(cmd, n):
    """The command under `timeout`, base64-carried so any quoting survives. Cut = exit 124, or 137 once the limit has
    passed (KILL after the grace); a crash before the limit is reported as itself. Without timeout/base64: runs as is."""
    b64 = base64.b64encode(cmd.encode("utf-8")).decode("ascii")
    stopped = STOPPED_FILE.replace("\\", "/")
    return (f'__c="$(echo {b64} | base64 -d 2>/dev/null)" || __c=""\n'
            f'if [ -z "$__c" ] || ! command -v timeout >/dev/null; then bash -c "$(echo {b64} | base64 -d)"; exit $?; fi\n'
            f'__t=$SECONDS; timeout -k {KILL_GRACE_S} {n} bash -c "$__c"; __rc=$?\n'
            f'if [ $__rc -eq 124 ] || {{ [ $__rc -eq 137 ] && [ $((SECONDS-__t)) -ge {n} ]; }}; then\n'
            f'  mkdir -p "$(dirname "{stopped}")"; printf "%s\\n%s\\n" "{_hash(cmd)}" "$(date +%s)" > "{stopped}"\n'
            f'  echo "{STOP_MSG.format(n=n)}"; fi\n'
            f'exit $__rc')


def _approved(cmd):
    """Use up his approval if it is for this exact command and still valid."""
    try:
        h, t = open(APPROVED_FILE, encoding="utf-8").read().split()[:2]
    except (OSError, ValueError):
        return False
    if h != _hash(cmd) or time.time() - float(t) > APPROVAL_MIN * 60:
        return False
    os.remove(APPROVED_FILE)
    return True


def pre(event, slot):
    """New tool_input for a PreToolUse event, or None to leave the command as it is."""
    if event.get("tool_name") != "Bash" or not slot.get("enabled"):
        return None
    inp = event.get("tool_input") or {}
    cmd = inp.get("command", "")
    if not cmd or len(cmd) > MAX_WRAP_CHARS or not runs_test(cmd, slot["pattern"]) or _approved(cmd):
        return None
    return dict(inp, command=wrap(cmd, int(slot["seconds"])))


def _asked_to_continue(path):
    """True when the assistant's last text reply is about a cut test (STOP_MSG told it to ask whether to continue)."""
    try:
        es = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    except (OSError, ValueError):
        return False
    for e in reversed(es):
        c = (e.get("message") or {}).get("content")
        if e.get("type") == "assistant" and isinstance(c, list):
            t = "\n".join(b.get("text", "") for b in c if b.get("type") == "text").strip()
            if t:
                return bool(re.search(r"\b(test|run|check)", t, re.I) and re.search(r"\b(continue|go on|keep going|again|proceed)\b", t, re.I))
    return False


def prompt(event, slot):
    """His short yes after a cut run -> approval for that command, only when the assistant's previous reply asked whether
    to continue the cut test. Returns the line to show, or None."""
    if not slot.get("enabled") or not os.path.exists(STOPPED_FILE) or not YES.match(event.get("prompt", "")):
        return None
    if not _asked_to_continue(event.get("transcript_path", "")):
        return None
    h = open(STOPPED_FILE, encoding="utf-8").read().split()[0]
    with open(APPROVED_FILE, "w", encoding="utf-8") as f:
        f.write(f"{h} {time.time()}\n")
    os.remove(STOPPED_FILE)
    return (f"test-limit: he approved continuing the run that was cut at {slot['seconds']} s. Re-run that exact command "
            f"once, within {APPROVAL_MIN} min; it will not be limited.")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre"
    try:
        event, slot = json.load(sys.stdin), _slot()
        if mode == "prompt":
            line = prompt(event, slot)
            if line:
                print(line)
            return
        new = pre(event, slot)
    except Exception:
        return
    if new:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow",
                                                 "updatedInput": new}}))


if __name__ == "__main__":
    main()
