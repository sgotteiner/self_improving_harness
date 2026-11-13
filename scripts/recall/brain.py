"""Bare brain: one cheap-model call with minimal context. Sets RECALL_BRAIN=1 so no recall hook re-fires."""
import json, os, shutil, subprocess, tempfile

CLAUDE = shutil.which("claude")
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "brain_calls.jsonl")
# --safe-mode: no CLAUDE.md, skills, MCP, hooks, settings. --tools "": no tool schemas. Floor measured: ~935 tokens/call.
FLAGS = ["-p", "--output-format", "json", "--model", "haiku", "--no-session-persistence", "--tools", "",
         "--safe-mode", "--exclude-dynamic-system-prompt-sections"]
_cwd = tempfile.mkdtemp(prefix="brain-")


def ask(prompt, system="Answer tersely and exactly as instructed.", tag=""):
    """Return (text, tokens). Tokens = all usage counters summed; appended to results/brain_calls.jsonl."""
    env = dict(os.environ, RECALL_BRAIN="1")
    p = subprocess.run([CLAUDE] + FLAGS + ["--system-prompt", system], input=prompt, capture_output=True,
                       text=True, encoding="utf-8", cwd=_cwd, env=env, timeout=180)
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
