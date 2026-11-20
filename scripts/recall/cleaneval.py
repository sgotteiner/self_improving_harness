"""Live eval of the merge path of cleandraft.py (real brain calls): each line of cleandraft_eval.jsonl is {label, expect: reject|pass,
lessons: [id | {id, lesson, right}]}. A case runs the grouping call on its lessons alone, then the checks on the wording it found:
`reject` = the grouping or a check refused, `pass` = all agreed. Exit 1 when a case differs from its label. Re-run after any change
to a prompt in cleandraft.py: python -I scripts/recall/cleandraft.py eval"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cleandraft, views

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cleandraft_eval.jsonl")


def run_case(items):
    """(outcome, detail) for lessons given as ids or {id, lesson, right}: outcome is `reject` or `pass`."""
    have = views.lessons()
    ls = {i: have[i] for i in items if isinstance(i, str)}
    ls.update({i["id"]: ("", i["lesson"], i["right"]) for i in items if isinstance(i, dict)})
    groups = [g for g in cleandraft.merges(ls) if set(g[0]) == set(ls)]
    if not groups:
        return "reject", "grouping: no MERGE of them all"
    ids, text = groups[0]
    why = cleandraft.why_not(text, [(i, ls[i][1], ls[i][2]) for i in ids], [])
    return ("reject", f"check: {why} | wording: {text}") if why else ("pass", f"wording: {text}")


def main():
    bad = 0
    for line in open(FILE, encoding="utf-8"):
        if line.strip():
            c = json.loads(line)
            got, detail = run_case(c["lessons"])
            bad += got != c["expect"]
            print(f"{'ok  ' if got == c['expect'] else 'FAIL'} {c['label']}: expected {c['expect']}, got {got} -- {detail}")
    return 1 if bad else 0
