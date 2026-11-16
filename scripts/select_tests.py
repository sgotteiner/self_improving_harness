"""Which suites of run_all_tests.py a change needs: files changed -> {suite name: (why, extra args)}. Pure mapping, no running."""
import os, re, subprocess

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TESTS = os.path.join(ROOT, "scripts", "recall", "tests")
CAPTURE = {"index", "embed", "retrieve", "validate", "casesave", "capture"}
DECISIONS = {"decisions", "eval_decisions"}
GATE = {"gate", "delegate", "delegvet", "turnfacts", "gatecases", "eval_gate", "suitecmd"}
SELF = {"scripts/run_all_tests.py", "scripts/select_tests.py"}


def changed_files(since=None):
    """Paths (relative to the setup root, forward slashes) changed since the last commit, or since `since`; plus untracked."""
    def git(*a):
        p = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return [l.strip() for l in p.stdout.splitlines() if l.strip()]
    return sorted(set(git("diff", "--name-only", "--relative", since or "HEAD") + git("ls-files", "--others", "--exclude-standard")))


def importers():
    """{module: [test module names that import it]} read from the recall test files."""
    out = {}
    for f in sorted(os.listdir(TESTS)):
        if f.startswith("test_") and f.endswith(".py"):
            for m in re.finditer(r"^\s*(?:import\s+([\w\s,]+)|from\s+(\w+)\s+import)", open(os.path.join(TESTS, f), encoding="utf-8").read(), re.M):
                for name in re.findall(r"\w+", m.group(1) or m.group(2)):
                    out.setdefault(name, set()).add(f[:-3])
    return {k: sorted(v) for k, v in out.items()}


def select(files):
    """{suite: (why, extra args)} in run order; empty when nothing relevant changed."""
    why, tests, all_recall, imp = {}, set(), False, importers()

    def pick(suite, f):
        why.setdefault(suite, []).append(os.path.basename(f))

    for f in files:
        d, base = os.path.dirname(f), os.path.splitext(os.path.basename(f))[0]
        if f in SELF:
            tests |= {"test_runall", "test_select"}; pick("recall tests", f)
        elif d == "scripts/recall/tests":
            if base.startswith("test_"):
                tests.add(base); pick("recall tests", f)
            elif f.endswith(".py"):
                all_recall = True; pick("recall tests", f)
        elif d == "scripts/recall" and f.endswith(".py"):
            hit = imp.get(base, [])
            elsewhere = base in CAPTURE | DECISIONS | GATE
            tests |= set(hit)
            if hit:
                pick("recall tests", f)
            elif not elsewhere:
                all_recall = True; pick("recall tests", f)  # unsure what covers it: the whole recall suite
            if base in CAPTURE:
                pick("capture check", f)
            if base in DECISIONS:
                pick("decision eval", f)
            if base in GATE:
                pick("gate eval", f); pick("gate eval (real brain)", f)
        elif f == "scripts/recall/gate_eval_set.jsonl":
            pick("gate eval", f); pick("gate eval (real brain)", f)
        elif f.startswith("cases/"):
            pick("capture check", f)
        elif f.startswith(("skills/sdd/", "skills/system-map/")):
            pick("sdd tests", f)
    order = ["recall tests", "sdd tests", "capture check", "gate eval", "gate eval (real brain)", "decision eval"]
    return {s: (", ".join(sorted(set(why[s]))[:4]) + " changed", [] if s != "recall tests" or all_recall else sorted(tests)) for s in order if s in why}
