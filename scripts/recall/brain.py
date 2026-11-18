"""Bare brain: one cheap-model call with minimal context. Sets RECALL_BRAIN=1 so no recall hook re-fires."""
import json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx

CLAUDE = shutil.which("claude")
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "brain_calls.jsonl")
# --safe-mode: no CLAUDE.md, skills, MCP, hooks, settings. --tools "": no tool schemas. Floor measured: ~935 tokens/call.
FLAGS = ["-p", "--output-format", "json", "--model", "haiku", "--no-session-persistence", "--tools", "",
         "--safe-mode", "--exclude-dynamic-system-prompt-sections"]
CWD = os.path.join(tempfile.gettempdir(), "recall-brain")  # one fixed empty dir, reused by every call
STATS = {"calls": 0, "429": 0, "models": {}}  # OpenRouter backend only (GIL makes += good enough for a count)
GEMINI_MODEL = "gemini-3.5-flash-lite"
TIMEOUT = 60 # seconds per call; hook.py and gate.py timeouts in settings.json are sized from it


def ask(prompt, system="Answer tersely and exactly as instructed.", tag=""):
    """Return (text, tokens). Tokens = all usage counters summed; appended to results/brain_calls.jsonl.
    Raises TimeoutError, without calling, when the process's time budget (ctx.BUDGET) is used up: the check is here so it
    runs before every call, whichever hook or stage makes it."""
    if ctx.over_budget(tag or "brain call"):
        raise TimeoutError("time budget of this hook is used up")
    backend = os.environ.get("RECALL_BRAIN_BACKEND")  # evals only; the hooks never set it
    if backend in ("openrouter", "gemini"):
        return (_openrouter if backend == "openrouter" else _gemini)(prompt, system, tag)
    os.makedirs(CWD, exist_ok=True)
    env = dict(os.environ, RECALL_BRAIN="1")
    p = subprocess.run([CLAUDE] + FLAGS + ["--system-prompt", system], input=prompt, capture_output=True,
                       text=True, encoding="utf-8", cwd=CWD, env=env, timeout=TIMEOUT)
    j = json.loads(p.stdout)
    u = j.get("usage", {})
    tok = sum(u.get(k, 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"))
    _log({"tag": tag, "tokens": tok, "cost": j.get("total_cost_usd", 0)})
    return j.get("result", "").strip(), tok


def _log(row):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except OSError:
        pass


def _secret(name):
    for l in open(os.path.join(ctx.ROOT, "secrets.local.env"), encoding="utf-8"):
        k, _, v = l.strip().partition("=")
        if k == name:
            return v.strip().strip("\"'")
    raise KeyError(name)


def _post(req):
    """POST with one retry on 429/5xx, after the wait the error names (Retry-After header or Gemini's retryDelay '12s'; max 30 s)."""
    for attempt in (0, 1):
        STATS["calls"] += 1
        try:
            return json.load(urllib.request.urlopen(req, timeout=TIMEOUT))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                STATS["429"] += 1
            if attempt or not (e.code == 429 or e.code >= 500):
                raise
            m = re.search(r'"retryDelay":\s*"([\d.]+)s"', e.read().decode("utf-8", "replace"))
            time.sleep(min(float(e.headers.get("Retry-After") or (m and m.group(1)) or 3), 30))


def _gemini(prompt, system, tag):
    """Gemini free tier, direct (evals only). Key goes in a header, not the URL, so no error text can show it."""
    body = json.dumps({"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"parts": [{"text": prompt}]}]}).encode()
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent", body, {
        "x-goog-api-key": _secret("GEMINI_API_KEY"), "Content-Type": "application/json", "User-Agent": "recall-brain"})
    j = _post(req)
    tok = (j.get("usageMetadata") or {}).get("totalTokenCount", 0)
    STATS["models"][GEMINI_MODEL] = STATS["models"].get(GEMINI_MODEL, 0) + 1
    _log({"tag": tag, "tokens": tok, "cost": 0, "model": GEMINI_MODEL})
    return (j["candidates"][0]["content"]["parts"][0].get("text") or "").strip(), tok


def _openrouter(prompt, system, tag):
    """Direct API call (no process spawn). 429/5xx: one retry after Retry-After (max 20 s), then raises. STATS counts for the evals."""
    body = json.dumps({"model": _secret("OPENROUTER_MODEL"), "messages": [
        {"role": "system", "content": system}, {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", body, {
        "Authorization": "Bearer " + _secret("OPENROUTER_API_KEY"), "Content-Type": "application/json", "User-Agent": "recall-brain"})
    j = _post(req)
    tok = (j.get("usage") or {}).get("total_tokens", 0)
    model = j.get("model", "?")
    STATS["models"][model] = STATS["models"].get(model, 0) + 1
    _log({"tag": tag, "tokens": tok, "cost": 0, "model": model})
    return (j["choices"][0]["message"].get("content") or "").strip(), tok


if __name__ == "__main__":
    print(ask("Reply with the single word OK", tag="selftest"))
