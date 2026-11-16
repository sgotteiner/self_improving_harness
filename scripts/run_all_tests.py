"""One command for every test and measurement of the setup (the tester agent runs this and nothing else): prints one line per
suite and a final PASSED or FAILED, with the failing lines only. Exit 0 = PASSED.
Usage: python -I scripts/run_all_tests.py [--eval]
Suites: the recall hooks' unit tests, the SDD tools' tests (node), the setup check (cases, sources, diaries), the gate eval
(labelled false alarms and real blocks replayed through the gate's code, free). Two suites call the real cheap model and cost
tokens, so each runs only when the files it measures changed since it last passed (or with --eval): the decision detector's
eval, and the gate eval's real-brain step. An unchanged one prints "skipped (unchanged)"."""
import os, re, subprocess, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RECALL = os.path.join(ROOT, "scripts", "recall")
PY = [sys.executable, "-I"]
GATE_FILES = [os.path.join(RECALL, f) for f in ("delegate.py", "delegvet.py", "turnfacts.py", "suitecmd.py", "gate_eval_set.jsonl")] + \
             [os.path.join(ROOT, "tasks", "delegation-draft.md"), os.path.join(ROOT, "CLAUDE.md")]
# (name, command, timeout, files whose change makes it run; None = always)
SUITES = [
    ("recall tests", PY + ["scripts/recall/tests/run_tests.py"], 300, None),
    ("sdd tests", ["node", "skills/sdd/scripts/test-sdd.js"], 300, None),
    ("capture check", PY + ["scripts/recall/capture.py", "check"], 300, None),
    ("gate eval", PY + ["scripts/recall/eval_gate.py"], 120, None),
    ("gate eval (real brain)", PY + ["scripts/recall/eval_gate.py", "--real"], 600, GATE_FILES),
    ("decision eval", PY + ["scripts/recall/eval_decisions.py"], 900, [os.path.join(RECALL, "decisions.py"), os.path.join(RECALL, "eval_decisions.py")]),
]
BAD = re.compile(r"\bFAIL(ED)?\b|\bERROR\b|\bBAD\b|Traceback|Error:|\[FAIL\]")


def stamp(name):
    return os.path.join(RECALL, "results", re.sub(r"\W+", "-", name) + ".stamp")


def changed(name, files):
    """True when any of `files` is newer than the stamp of the last passing run (or there is no stamp)."""
    try:
        last = os.path.getmtime(stamp(name))
    except OSError:
        return True
    return any(os.path.getmtime(f) > last for f in files if os.path.exists(f))


def run(cmd, timeout):
    """(ok, one-line summary, [failing lines])."""
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"could not run: {e!r}", []
    lines = [l.strip() for l in (p.stdout + "\n" + p.stderr).splitlines() if l.strip()]
    summary = next((l for l in reversed(lines) if re.search(r"\bpassed\b|^OK$|^Ran \d+|^check:|decisions caught|gate eval|FAILED", l)), lines[-1] if lines else "no output")
    return p.returncode == 0, summary[:110], [l[:200] for l in lines if BAD.search(l)][:12] if p.returncode else []


def main(force=False):
    failed = []
    for name, cmd, timeout, files in SUITES:
        if files and not force and not changed(name, files):
            print(f"SKIP  {name}: skipped (unchanged)", flush=True)
            continue
        ok, summary, bad = run(cmd, timeout)
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {summary}", flush=True)
        if ok and files:
            os.makedirs(os.path.dirname(stamp(name)), exist_ok=True)
            open(stamp(name), "w").close()
        failed += [f"{name}: {l}" for l in bad] or ([] if ok else [f"{name}: {summary}"])
    print("PASSED" if not failed else "FAILED")
    for l in failed:
        print("  " + l)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main("--eval" in sys.argv))
