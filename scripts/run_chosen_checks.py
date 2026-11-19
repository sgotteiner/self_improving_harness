"""One command for the tests of what changed (the tester agent runs this and nothing else): prints one line per chosen suite
and a final PASSED or FAILED, with the failing lines only. Exit 0 = PASSED.
Usage: python -I scripts/run_chosen_checks.py [--files <f> ...] [--since <ref>] [--all] [--eval]
  --files <f> ..  the files the task changed (repo-relative): selection uses exactly these. A CHOOSE line says why for each
                  suite, and the recall unit tests run per test file (only the ones importing a changed module).
                  Nothing relevant changed -> "nothing to test". A changed .py no check covers -> "not covered by any check: <f>".
  (default)       without --files: the files changed since the last commit (git diff HEAD + untracked); a line says so.
  --since <ref>   the files changed since <ref> instead, e.g. HEAD~1 for the commit about to be pushed.
  --all           every suite, regardless of changes: only when the owner asks for a full regression run.
Selection rules are in select_tests.py.
Suites: the recall hooks' unit tests, the SDD tools' tests (node), the setup check (cases, sources, diaries)."""
import os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script's own folder
import select_tests

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RECALL = os.path.join(ROOT, "scripts", "recall")
PY = [sys.executable, "-I"]
# (name, command, timeout, files whose change makes it run; None = always)
SUITES = [
    ("recall tests", PY + ["scripts/recall/tests/run_tests.py"], 300, None),
    ("sdd tests", ["node", "skills/sdd/scripts/test-sdd.js"], 300, None),
    ("capture check", PY + ["scripts/recall/capture.py", "check"], 300, None),
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


def main(force=False, chosen=None, uncovered=()):
    """chosen: {suite name: (why, extra args)} from select_tests.select; None = every suite."""
    failed = []
    for f in uncovered:
        print(f"not covered by any check: {f}")
    if chosen is not None and not chosen:
        print("nothing to test (no changed file maps to a suite)")
    for name, cmd, timeout, files in SUITES:
        if chosen is not None:
            if name not in chosen:
                continue
            print(f"CHOOSE  {name}: {chosen[name][0]}", flush=True)
            cmd = cmd + chosen[name][1]
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


def repo_path(x):
    """Any form a caller passes (./x, absolute C:\\..., Git Bash /c/...) -> repo-relative with '/', as select_tests expects."""
    m = re.match(r"^/([a-zA-Z])/(.*)", x)
    if m:
        x = f"{m.group(1)}:/{m.group(2)}"
    x = x if os.path.isabs(x) else os.path.join(ROOT, x)  # repo-relative, whatever folder the runner was started from
    return os.path.relpath(os.path.normpath(x), ROOT).replace("\\", "/")


if __name__ == "__main__":
    a = sys.argv[1:]
    since = a[a.index("--since") + 1] if "--since" in a and a.index("--since") + 1 < len(a) else None
    if "--files" in a:
        files = []
        for x in a[a.index("--files") + 1:]:
            if x.startswith("--"):
                break
            files.append(repo_path(x))
    else:
        files = select_tests.changed_files(since)
        print(f"no --files given: using the {len(files)} files changed since {since or 'the last commit'}")
    every = "--all" in a
    sys.exit(main("--eval" in a, None if every else select_tests.select(files), [] if every else select_tests.uncovered(files)))
