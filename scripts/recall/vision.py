"""Vision injection (switch `vision` in slots.json). VISION.md is injected like a rule: into every human message of the
main session (hook.py prints text() first) and into every subagent's context (a SubagentStart hook, settings.json, runs
`vision.py subagent` and returns it as additionalContext). Nothing is copied: the text is read from VISION.md on each
call, so editing the file changes what every message and agent sees. Fails open: a missing file or any error means no
injection, never a blocked message or agent."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx

FILE = os.path.join(ctx.ROOT, "VISION.md")


def text():
    """VISION.md without its heading line, or '' if the file is missing or empty."""
    try:
        lines = open(FILE, encoding="utf-8").read().strip().splitlines()
    except OSError:
        return ""
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def lines():
    """[text] for the main session's hook output, [] when the switch is off or there is no text."""
    t = text() if ctx.enabled("vision") else ""
    return [t] if t else []


def subagent_output():
    """The SubagentStart hook's JSON for the current stdin payload, or '' (switch off, no text: output nothing)."""
    t = text() if ctx.enabled("vision") else ""
    if not t:
        return ""
    return json.dumps({"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": t}})


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "subagent":
    try:
        sys.stdin.read()
        o = subagent_output()
        if o:
            print(o, flush=True)
    except Exception as e:
        ctx.log(f"vision: subagent hook failed: {e!r}")
    sys.exit(0)
