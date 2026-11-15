"""Bare brain: one cheap-model call with minimal context. Sets RECALL_BRAIN=1 so no recall hook re-fires."""
import json, os, shutil, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx

CLAUDE = shutil.which("claude")
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "brain_calls.jsonl")
# --safe-mode: no CLAUDE.md, skills, MCP, hooks, settings. --tools "": no tool schemas. Floor measured: ~935 tokens/call.
FLAGS = ["-p", "--output-format", "json", "--model", "haiku", "--no-session-persistence", "--tools", "",
         "--safe-mode", "--exclude-dynamic-system-prompt-sections"]
CWD = os.path.join(tempfile.gettempdir(), "recall-brain")  # one fixed empty dir, reused by every call
TIMEOUT = 60  # seconds per call; hook.py and gate.py timeouts in settings.json are sized from it


def ask(prompt, system="Answer tersely and exactly as instructed.", tag=""):
    """Return (text, tokens). Tokens = all usage counters summed; appended to results/brain_calls.jsonl.
    Raises TimeoutError, without calling, when the process's time budget (ctx.BUDGET) is used up: the check is here so it
    runs before every call, whichever hook or stage makes it."""
    if ctx.over_budget(tag or "brain call"):
        raise TimeoutError("time budget of this hook is used up")
    os.makedirs(CWD, exist_ok=True)
    env = dict(os.environ, RECALL_BRAIN="1")
    p = subprocess.run([CLAUDE] + FLAGS + ["--system-prompt", system], input=prompt, capture_output=True,
                       text=True, encoding="utf-8", cwd=CWD, env=env, timeout=TIMEOUT)
    j = json.loads(p.stdout)
    u = j.get("usage", {})
    tok = sum(u.get(k, 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"))
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"tag": tag, "tokens": tok, "cost": j.get("total_cost_usd", 0)}) + "\n")
    except OSError:
        pass
    return j.get("result", "").strip(), tok


if __name__ == "__main__":
    print(ask("Reply with the single word OK", tag="selftest"))
