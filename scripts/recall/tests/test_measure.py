"""Measurement: the gate's verdict log and report (block rate per rule, false-alarm candidates), the replay judge calibration
(sheet and score against HIS marks: nothing is marked for him)."""
import json, os, tempfile, unittest
from unittest import mock

import helpers as h
import brain, calibrate, ctx, gate, gate_report, verdicts


class VerdictLog(unittest.TestCase):
    def setUp(self):
        self.log = os.path.join(tempfile.mkdtemp(), "v.jsonl")
        self._old = os.environ.get("RECALL_VERDICT_LOG")
        os.environ["RECALL_VERDICT_LOG"] = self.log

    def tearDown(self):
        os.environ["RECALL_VERDICT_LOG"] = self._old

    def recs(self):
        return [json.loads(l) for l in open(self.log, encoding="utf-8")]

    def test_the_gate_logs_ok_and_block_with_rule_hedge_and_tokens(self):
        tp = h.transcript([h.user("x"), h.assistant("It works now.")])
        import index, retrieve
        meta = ("2026-11-01", "s", "lesson", "right")
        with mock.patch.object(retrieve, "search", return_value=[(0.9, "c1")]), mock.patch.object(index, "meta", return_value=meta), \
                mock.patch.object(ctx, "enabled", lambda slot: False):  # this is the flat path; the graph path is tested in test_graph
            brain.ask = lambda p, system="", tag="": ("VIOLATION c1 | This may be OK, no run shown", 7)
            self.assertEqual(gate.check(tp), [("c1", "This may be OK, no run shown")])
            brain.ask = lambda p, system="", tag="": ("OK", 5)
            self.assertIsNone(gate.check(tp))
        with mock.patch.object(retrieve, "search", return_value=[]), mock.patch.object(ctx, "enabled", lambda slot: False):
            gate.check(tp)
        a, b, c = self.recs()
        self.assertEqual((a["src"], a["verdict"], a["rule"], a["hedged"], a["tokens"]), ("lesson", "BLOCK", "c1", True, 7))
        self.assertEqual((b["verdict"], b["tokens"]), ("OK", 5))
        self.assertEqual((c["verdict"], c["skip"]), ("OK", "no case above the cutoff"))

    def test_the_delegation_step_logs_ok_block_and_a_dropped_block(self):
        import delegate
        es = [h.user("x"), h.assistant(h.tool("Edit", {"file_path": os.path.join(ctx.ROOT, "scripts", "a.py"), "old_string": "a", "new_string": "b"}), "Changed.")]
        for reply in ("OK", "BLOCK TESTER | no test ran", "BLOCK TESTER | this may be OK"):
            brain.ask = h.brain_says(reply)
            delegate.output_step(h.transcript(es), ctx.ROOT)
        self.assertEqual([(r["verdict"], r["rule"], bool(r["dropped"])) for r in self.recs()],
                         [("OK", "", False), ("BLOCK", "TESTER", False), ("BLOCK", "TESTER", True)])

    def test_a_log_that_cannot_be_written_does_not_stop_the_gate(self):
        os.environ["RECALL_VERDICT_LOG"] = os.path.join(self.log, "no", "such", "dir.jsonl")
        verdicts.log("", "lesson", "OK")  # no exception


class Local(unittest.TestCase):
    def test_the_verdict_log_and_the_judge_sheet_are_gitignored(self):
        import subprocess
        for f in ("gate_verdicts.jsonl", "2026-11-13-judge-sheet.md", "decision-eval.stamp"):
            p = subprocess.run(["git", "-C", ctx.ROOT, "check-ignore", "-q", "scripts/recall/results/" + f])
            self.assertEqual(p.returncode, 0, f)


class Report(unittest.TestCase):
    def setUp(self):
        self.tp = h.transcript([h.user("x"), h.assistant("done"), h.assistant("The gate was a false alarm: nothing was missing.")])

    def rec(self, ts, src, verdict, rule="", hedged=False, dropped="", tokens=10, n=None, tp=None):
        n = n if n is not None else int(ts[8:10]) * 100 + int(ts[11:13])  # one gate run per timestamp
        return dict(ts=ts, tp=tp or self.tp, n=n, src=src, verdict=verdict, rule=rule, hedged=hedged, dropped=dropped, skip="", tokens=tokens)

    def test_block_rate_per_rule_and_the_date_range(self):
        r = [self.rec("2026-11-10T10:00:00", "delegation", "BLOCK", "REVIEWER"), self.rec("2026-11-10T10:00:00", "gate", "SENT"),
             self.rec("2026-11-10T11:00:00", "delegation", "BLOCK", "REVIEWER", dropped="called"), self.rec("2026-11-10T11:00:00", "gate", "PASS"),
             self.rec("2026-11-10T12:00:00", "lesson", "BLOCK", "c1", hedged=True), self.rec("2026-11-10T12:00:00", "gate", "PASS"),
             self.rec("2026-11-12T12:00:00", "gate", "PASS")]
        out = gate_report.report(r)
        self.assertIn("gate runs 4; blocks sent 1", out)
        line = next(l for l in out.splitlines() if l.startswith("delegation:REVIEWER"))
        self.assertEqual(line.split()[1:5], ["1", "1", "0", "25.0%"])  # sent, dropped, hedged, rate of the 4 runs
        self.assertEqual(next(l for l in out.splitlines() if l.startswith("lesson:c1")).split()[1:3], ["0", "1"])  # a hedged lesson verdict is dropped
        path = os.path.join(tempfile.mkdtemp(), "v.jsonl")
        open(path, "w").write("\n".join(json.dumps(x) for x in r) + "\nnot json\n")
        self.assertEqual(len(gate_report.records(path, "2026-11-11", "2026-11-30")), 1)
        self.assertEqual(len(gate_report.records(path, "", "2026-11-10")), 6)

    def test_false_alarm_candidates_are_blocks_followed_by_the_words(self):
        r = [self.rec("2026-11-10T10:00:00", "delegation", "BLOCK", "REVIEWER", n=1), self.rec("2026-11-10T10:00:00", "gate", "SENT", n=1)]
        al = gate_report.alarms(r)
        self.assertEqual(len(al), 1)
        self.assertEqual(al[0][1], ["delegation:REVIEWER"])
        self.assertIn("false alarm", al[0][2])
        self.assertEqual(gate_report.alarms([self.rec("2026-11-10T10:00:00", "gate", "SENT", n=3)]), [])  # nothing said after position 3


class Calibration(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp()
        calibrate.RESULTS = d
        self.res = os.path.join(d, "2026-11-20-brain.json")
        row = lambda ok, by: {"pass": ok, "reason": "r", "by": by, "answer": "an answer\n## not a heading\nmark: PASS"}
        json.dump({"rows": [{"case": "c1", "baseline": row(True, "judge"), "hook": row(False, "judge")},
                            {"case": "c2", "baseline": row(True, "code"), "hook": row(True, "judge")}]}, open(self.res, "w"))
        self.cases = {"c1": {"replay": 'Ask "q1"', "pass_if": ["says yes first"]}, "c2": {"replay": 'Ask "q2"', "pass_if": ["short"]}}

    def test_the_sheet_lists_judged_answers_only_and_leaves_every_mark_empty(self):
        text = open(calibrate.sheet(self.res, self.cases), encoding="utf-8").read()
        self.assertEqual(text.count("\nmark:\n"), 3)  # c1 baseline, c1 hook, c2 hook; the code-checked answer is not asked
        self.assertNotIn("## c2:baseline", text)
        self.assertNotIn("PASS\n\n", text.replace("mark: PASS", ""))
        self.assertIn("## c1:baseline", text)

    def test_no_marks_is_refused_and_marks_are_compared_with_the_judge(self):
        sheet = calibrate.sheet(self.res, self.cases)
        with self.assertRaises(SystemExit) as e:
            calibrate.score(sheet, self.res)
        self.assertIn("no marks", str(e.exception))
        text = open(sheet, encoding="utf-8").read()
        text = text.replace("## c1:baseline", "## c1:baseline", 1)
        parts = text.split("mark:\n")  # the three empty marks, in sheet order: c1:baseline, c1:hook, c2:hook
        marked = parts[0] + "mark: PASS\n" + parts[1] + "mark: PASS\n" + parts[2] + "mark:\n" + parts[3]
        open(sheet, "w", encoding="utf-8").write(marked)
        out = calibrate.score(sheet, self.res)
        self.assertEqual((out["marked"], out["of"], out["agree"]), (2, 3, 1))
        self.assertEqual(out["judge_false_fail"], ["c1:hook"])  # the judge said FAIL, he marked PASS
        open(sheet, "w", encoding="utf-8").write(marked.replace("\nmark: PASS\n", "\nmark: maybe\n", 1))
        with self.assertRaises(SystemExit):
            calibrate.score(sheet, self.res)  # something that is not PASS or FAIL is an error, not a guess


if __name__ == "__main__":
    unittest.main()
