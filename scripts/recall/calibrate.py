"""Calibrates replay's judge (replay.judge, a cheap model) against HIS marks. Nothing here marks an answer for him.
  sheet [results.json]  writes results/<date>-judge-sheet.md: each answer the judge ruled on, with the task and the criteria
                        and an empty `mark:` line (the judge's verdict is not shown, so it cannot sway him). Latest results file by default.
  score <sheet.md> [results.json]  reads his marks (PASS or FAIL after `mark:`), compares them with the judge's verdicts and prints
                        agreement, the judge's false passes and false fails; writes results/<date>-judge-calibration.json.
                        Unmarked entries are left out and counted; no marks at all -> exit 1."""
import glob, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import index

RESULTS = os.path.join(index.HERE, "results")
MARK = re.compile(r"^## (\S+)\n(.*?)^mark:[ \t]*(\S*)", re.S | re.M)


def latest():
    files = sorted(glob.glob(os.path.join(RESULTS, "*-brain.json")))
    if not files:
        raise SystemExit("no replay results: run scripts/recall/replay.py first")
    return files[-1]


def judged(results):
    """{'<case>:<run>': row} of the replay answers the judge (not the code check) ruled on."""
    return {f"{r['case']}:{run}": r[run] for r in results["rows"] for run in ("baseline", "hook") if r[run]["by"] == "judge"}


def esc(text):
    """A line of the answer that looks like a heading or the mark line must not be read as one."""
    return re.sub(r"^(##|mark:)", r"> \1", text, flags=re.M)


def sheet(path, cases=None):
    res = json.load(open(path, encoding="utf-8"))
    cases = cases or {c["id"]: c for c in (index.parse(f) for f in index.case_files())}
    out = ["# Judge calibration sheet", "", f"From {os.path.basename(path)}. After each `mark:` write PASS or FAIL: does the answer meet ALL "
           "the criteria? Leave it empty when unsure.", ""]
    for k, row in judged(res).items():
        c = cases.get(k.split(":")[0], {})
        crit = c.get("pass_if") or []
        out += [f"## {k}", f"Task: {c.get('replay', '(case file not found)')}", "Criteria:"] + [f"- {x}" for x in crit] + \
               ["", "Answer:", "", esc(row["answer"]), "", "mark:", ""]
    dest = os.path.join(RESULTS, os.path.basename(path)[:10] + "-judge-sheet.md")
    open(dest, "w", encoding="utf-8").write("\n".join(out))
    return dest


def score(sheet_path, path):
    res = json.load(open(path, encoding="utf-8"))
    rows, marks, bad = judged(res), {}, []
    for k, _, m in MARK.findall(open(sheet_path, encoding="utf-8").read()):
        if m.upper() in ("PASS", "FAIL"):
            marks[k] = m.upper() == "PASS"
        elif m:
            bad.append(f"{k}: '{m}' is not PASS or FAIL")
    marks = {k: v for k, v in marks.items() if k in rows}
    if bad or not marks:
        raise SystemExit("\n".join(bad) or "no marks in the sheet: nothing to calibrate against (marks are his; none are filled in here)")
    fp = [k for k, v in marks.items() if rows[k]["pass"] and not v]  # judge PASS, he FAIL
    fn = [k for k, v in marks.items() if not rows[k]["pass"] and v]  # judge FAIL, he PASS
    out = dict(marked=len(marks), of=len(rows), agree=len(marks) - len(fp) - len(fn), judge_false_pass=fp, judge_false_fail=fn)
    dest = os.path.join(RESULTS, os.path.basename(path)[:10] + "-judge-calibration.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=1)
    print(f"his marks {out['marked']} of {out['of']} judged answers; judge agrees on {out['agree']}; false passes {fp}; false fails {fn}\nWritten {dest}")
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["sheet"]:
        print("written", sheet(a[1] if len(a) > 1 else latest()))
    elif a[:1] == ["score"] and len(a) > 1:
        score(a[1], a[2] if len(a) > 2 else latest())
    else:
        raise SystemExit(__doc__)
