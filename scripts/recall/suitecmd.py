"""Which Bash commands run a test suite or measurement (the main session must hand those to the tester agent), and what a
result or a review text says (the purpose fell short; fixes asked for). Real commands only: the interpreter and the script
name are read from the command, so a comment, a `--out test.json` or the name inside a grep never counts."""
import os, re

SCRIPT = re.compile(r"^(test_[\w.-]*\.py|test-[\w.-]*\.js|run_tests\.py|run_chosen_checks\.py|eval_\w+\.py|replay\.py)$")
READ_ONLY = re.compile(r"^\s*(grep|rg|cat|ls|git|head|tail|sed|echo|find|wc|diff)\b")  # small reads: never a suite run
FELL = re.compile(r"\bFAIL(ED)?\b|\bfell short\b|\b[1-9]\d* (failed|failures?|errors?)\b|Traceback", re.I)  # a result: the purpose was not met
FIXES = re.compile(r"fix (these |this |it |them )?first|fix before|must be fixed|must fix|blocking|do not (commit|merge)|not ready", re.I)  # a review: fixes asked for


def _segment(seg):
    w = [x.strip("'\"") for x in seg.split()]
    while w and "=" in w[0] and not w[0].startswith("-"):  # leading VAR=value
        w = w[1:]
    if not w:
        return False
    exe, args = os.path.basename(w[0].replace("\\", "/")).lower().removesuffix(".exe"), w[1:]
    if exe in ("pytest", "jest", "vitest"):
        return True
    if exe in ("npm", "npx"):
        return args[:1] == ["test"] or args[:2] == ["run", "test"] or (exe == "npx" and args[:1] in (["jest"], ["vitest"], ["pytest"]))
    if exe in ("go", "cargo"):
        return args[:1] == ["test"]
    if exe.startswith("python") or exe in ("py", "node", "bash", "sh"):
        if "-c" in args:
            return False
        if "-m" in args and args[args.index("-m") + 1:args.index("-m") + 2] in (["pytest"], ["unittest"]):
            return True
        script = next((a for a in args if not a.startswith("-")), "")
        name = os.path.basename(script.replace("\\", "/"))
        return bool(SCRIPT.match(name)) or (name == "capture.py" and "check" in args)
    return False


def is_suite(command):
    """True when a Bash command runs a test suite or a measurement (run_tests.py, test-sdd.js, eval_*.py, pytest, npm test, ...)."""
    command = re.sub(r"(^|\s)#.*$", "", command, flags=re.M)  # a comment is not a command
    return any(_segment(s) for s in re.split(r"&&|\|\||[;|\n]", command) if not READ_ONLY.match(s))
