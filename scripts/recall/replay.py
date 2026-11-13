"""Replay each case in a fresh headless session, baseline (RECALL_HOOK=0) vs hook on; judge vs pass_if."""
import datetime, json, os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import index

CLAUDE = shutil.which("claude")
# plan mode: the replayed sessions must not really install, edit settings or write files on this machine
BASE = [CLAUDE, "-p", "--output-format", "json", "--permission-mode", "plan", "--no-session-persistence"]


def ask(prompt, cwd, extra=(), hook=True, model=None):
    env = dict(os.environ)
    env.pop("RECALL_HOOK", None)
    if not hook:
        env["RECALL_HOOK"] = "0"
    cmd = BASE + list(extra) + (["--model", model] if model else [])
    p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", cwd=cwd, env=env, timeout=600)
    j = json.loads(p.stdout)
    return j.get("result", ""), j.get("total_cost_usd", 0.0), sum(v for k, v in j.get("usage", {}).items() if k.endswith("tokens") and isinstance(v, int))


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
    txt, cost, tok = ask(p, cwd, hook=False, model="haiku")
    return txt.strip().upper().startswith("PASS"), txt.strip().splitlines()[0][:140], cost, tok


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
            ans, cs, tk = ask(prompt, cwd, extra, hook)
            v = code_check(c["id"], ans)
            how = "code"
            if v is None:
                ok, why, jc, jt = judge(c, ans, cwd)
                v, how, cs, tk = (ok, why), "judge", cs + jc, tk + jt
            cost, tok = cost + cs, tok + tk
            row[name] = {"pass": v[0], "reason": v[1], "by": how, "answer": ans[:1500]}
        out.append(row)
    d = datetime.date.today().isoformat()
    path = os.path.join(index.HERE, "results", d + ".json")
    json.dump({"date": d, "judge_calibrated": False, "total_tokens": tok, "total_cost_usd": round(cost, 4), "rows": out},
              open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{'case':34} {'baseline':9} {'hook':6} reason (hook run)")
    for r in out:
        f = lambda x: "PASS" if x["pass"] else "FAIL"
        print(f"{r['case']:34} {f(r['baseline']):9} {f(r['hook']):6} [{r['hook']['by']}] {r['hook']['reason']}")
    n = len(out)
    print(f"\npass: baseline {sum(r['baseline']['pass'] for r in out)}/{n}, hook {sum(r['hook']['pass'] for r in out)}/{n}")
    print(f"tokens {tok}, cost ${cost:.4f}. Written {path}")
    print("NOTE: the haiku judge is not yet calibrated against the owner's labels; plan mode, so tool-use signals are not truly tested.")


if __name__ == "__main__":
    main()
