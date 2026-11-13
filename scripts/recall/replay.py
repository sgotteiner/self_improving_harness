"""Replay each case in a fresh headless session, baseline (hooks off via env) vs hooks on (input hook + output gate);
judge vs pass_if with a bare brain call. Tokens per session and per brain call are recorded."""
import datetime, json, os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain, index

CLAUDE = shutil.which("claude")
# plan mode: the replayed sessions must not really install, edit settings or write files on this machine
BASE = [CLAUDE, "-p", "--output-format", "json", "--permission-mode", "plan", "--no-session-persistence"]


def ask(prompt, cwd, extra=(), hook=True, model=None):
    env = dict(os.environ)
    env["RECALL_CAPTURE"] = "0"  # replays must not write pending cases or occurrences
    for v in ("RECALL_HOOK", "RECALL_GATE"):
        env.pop(v, None)
        if not hook:
            env[v] = "0"
    cmd = BASE + list(extra) + (["--model", model] if model else [])
    p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", cwd=cwd, env=env, timeout=600)
    j = json.loads(p.stdout)
    return j.get("result", ""), j.get("total_cost_usd", 0.0), sum(v for k, v in j.get("usage", {}).items() if k.endswith("tokens") and isinstance(v, int))


def brain_tokens():
    """Tokens of all brain calls logged so far (hook and gate calls made inside replayed sessions land here)."""
    try:
        return sum(json.loads(l)["tokens"] for l in open(brain.LOG, encoding="utf-8"))
    except OSError:
        return 0


def code_check(cid, ans):
    """Deterministic verdicts where pass_if gives concrete signals; None = needs the judge."""
    low = ans.lower().strip()
    if cid == "missing-why-not-flagged":
        ok = low.startswith("why: not given") and "missing:" in low
        return ok, "starts with 'Why: not given' and has a Missing: line" if ok else "no 'Why: not given' start / Missing: line"
    if cid == "answer-what-he-wants-to-know":
        first = re.split(r"(?<=[.!?])\s", low, 1)[0]
        bad = [w for w in ("not exactly", "technically", "strictly speaking") if w in low[:300]]
        ok = bool(re.search(r"\byes\b", first)) and not bad
        return ok, "first sentence has 'yes', no hedge opener" if ok else f"first sentence: {first[:60]!r} hedges: {bad}"
    return None


def judge(case, ans, cwd):
    p = ("Judge an AI answer against checkable criteria. Reply with PASS or FAIL, then ' - ' and one short reason.\n"
         f"Task given to the AI: {case['replay']}\nCriteria (all must hold):\n- " + "\n- ".join(case["pass_if"]) +
         f"\n\nAnswer:\n{ans[:4000]}")
    txt, tok = brain.ask(p, tag="judge")
    return txt.upper().startswith("PASS"), txt.splitlines()[0][:140], 0.0, tok


def main():
    cases = [index.parse(f) for f in index.case_files()]
    cwd = tempfile.mkdtemp(prefix="replay-")
    out, cost, tok = [], 0.0, 0
    for c in cases:
        m = re.search(r'"(.+?)"', c["replay"])
        prompt = m.group(1) if m else c["replay"]
        extra = ["--agent", "implementer"] if "implementer agent" in c["replay"] else []
        row = {"case": c["id"]}
        for name, hook in (("baseline", False), ("hook", True)):
            b0 = brain_tokens()
            ans, cs, tk = ask(prompt, cwd, extra, hook)
            bt = brain_tokens() - b0  # hook + gate brain calls inside this session
            st = tk
            v = code_check(c["id"], ans)
            how = "code"
            if v is None:
                ok, why, jc, jt = judge(c, ans, cwd)
                v, how, cs, tk = (ok, why), "judge", cs + jc, tk + jt
            cost, tok = cost + cs, tok + tk + bt  # bt: hook/gate brain calls, not in the session usage
            row[name] = {"pass": v[0], "reason": v[1], "by": how, "answer": ans[:1500], "session_tokens": st, "brain_tokens": bt}
        out.append(row)
    d = datetime.date.today().isoformat()
    path = os.path.join(index.HERE, "results", d + "-brain.json")
    json.dump({"date": d, "judge_calibrated": False, "total_tokens": tok, "total_cost_usd": round(cost, 4), "rows": out},
              open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{'case':34} {'baseline':9} {'hook':6} {'tok base':>9} {'tok hook':>9} {'brain tok':>9}  reason (hook run)")
    for r in out:
        f = lambda x: "PASS" if x["pass"] else "FAIL"
        print(f"{r['case']:34} {f(r['baseline']):9} {f(r['hook']):6} {r['baseline']['session_tokens']:9d} {r['hook']['session_tokens']:9d} {r['hook']['brain_tokens']:9d}  [{r['hook']['by']}] {r['hook']['reason']}")
    n = len(out)
    print(f"\npass: baseline {sum(r['baseline']['pass'] for r in out)}/{n}, hook {sum(r['hook']['pass'] for r in out)}/{n}")
    print(f"tokens {tok}, cost ${cost:.4f}. Written {path}")
    print("NOTE: the haiku judge is not yet calibrated against the owner's labels; plan mode, so tool-use signals are not truly tested.")


if __name__ == "__main__":
    main()
