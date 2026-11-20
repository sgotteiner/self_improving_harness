"""Shadow select: every gate call writes one line, the verdict is untouched, a failure is ignored, the report counts per lesson."""
import json, os, sqlite3, sys, time, unittest
from unittest import mock

import numpy as np

import brain, ctx, embed, gate, retrieve, shadow
from propbase import Base


class Shadow(Base):
    def setUp(self):
        super().setUp()
        self.log = os.path.join(self.d, "shadow.jsonl")
        for p in (mock.patch.dict(os.environ, {"RECALL_SHADOW_LOG": self.log}),
                  mock.patch.object(ctx, "enabled", side_effect=lambda s: s in ("recall-all-lessons", "shadow-select")),
                  mock.patch.object(gate.verdicts, "log"), mock.patch.object(ctx, "last_turn", return_value=("it works", ["Bash: ls"]))):
            p.start()
            self.addCleanup(p.stop)

    def lines(self):
        return [json.loads(l) for l in open(self.log, encoding="utf-8")] if os.path.exists(self.log) else []

    def gate(self, answer, search):
        with mock.patch.object(brain, "ask", return_value=(answer, 1)), mock.patch.object(retrieve, "search", side_effect=search) as s:
            return gate.check("tp"), s

    def test_every_gate_call_writes_one_line_with_what_all_named_and_select_top_and_the_verdict_is_the_same(self):
        found, s = self.gate("VIOLATION a | broke it", lambda *a, **k: [(0.8, "a"), (0.71, "b"), (0.5, "c")])
        self.assertEqual(found, [("a", "broke it")])
        self.gate("OK", lambda *a, **k: [])
        r = self.lines()
        self.assertEqual(len(r), 2)
        self.assertEqual((r[0]["all_named"], r[0]["select_top"]), (["a"], [["a", 0.8], ["b", 0.71]]))  # under RELEVANCE_MIN is cut
        self.assertEqual((r[1]["all_named"], r[1]["select_top"]), ([], []))
        self.assertTrue(r[0]["date"] and r[0]["transcript"] == "tp")
        self.assertEqual(s.call_args[0][1:], (shadow.TOP_K, "emb"))

    def test_a_failing_select_never_changes_the_verdict_and_off_writes_nothing(self):
        found, _ = self.gate("VIOLATION a | broke it", OSError("model gone"))
        self.assertEqual(found, [("a", "broke it")])
        self.assertEqual(self.lines(), [])
        with mock.patch.object(ctx, "enabled", side_effect=lambda s: s == "recall-all-lessons"):
            self.gate("OK", lambda *a, **k: [(0.9, "a")])
        self.assertEqual(self.lines(), [])

    def test_the_verdict_is_logged_before_shadow_runs_and_a_shadow_that_cannot_load_changes_nothing(self):
        order = []
        gate.verdicts.log.side_effect = lambda *a, **k: order.append("verdict")
        with mock.patch.object(shadow, "record", side_effect=lambda *a: order.append("shadow")):
            self.gate("OK", lambda *a, **k: [])
        self.assertEqual(order, ["verdict", "shadow"])
        with mock.patch.dict(sys.modules, {"shadow": None}):  # the import fails
            found, _ = self.gate("VIOLATION a | broke it", lambda *a, **k: [])
        self.assertEqual(found, [("a", "broke it")])

    def test_shadow_is_skipped_when_less_than_the_margin_of_the_budget_is_left(self):
        with mock.patch.object(ctx, "T0", time.monotonic() - ctx.BUDGET + shadow.MARGIN - 1):
            _, s = self.gate("OK", lambda *a, **k: [(0.9, "a")])
        s.assert_not_called()
        self.assertEqual(self.lines(), [])

    def test_a_hung_shadow_step_is_given_up_after_its_bound(self):
        with mock.patch.object(shadow, "MAX_RUN", 0.2), mock.patch.object(shadow, "_write", side_effect=lambda *a: time.sleep(2)):
            t = time.monotonic()
            shadow.record("tp", "x", [], [])
        self.assertLess(time.monotonic() - t, 1.5)

    def test_the_query_is_not_cached_in_vectors_db_but_the_lessons_are(self):
        db = os.path.join(self.d, "v.db")
        rows = lambda: sqlite3.connect(db).execute("SELECT COUNT(*) FROM v").fetchone()[0]
        with mock.patch.object(embed, "DB", db), mock.patch.dict(embed._models, {"fastembed": lambda t: np.ones((len(t), 4))}):
            embed.scores(["q one"], {"a": ["lesson text"]}, cache_query=False)
            self.assertEqual(rows(), 1)  # the lesson text only
            embed.scores(["q two"], {"a": ["lesson text"]})
            self.assertEqual(rows(), 2)  # the default still caches a query

    def test_the_report_counts_per_lesson_named_by_all_how_often_select_had_it_and_overall(self):
        rows = [{"all_named": ["a"], "select_top": [["a", .8]]}, {"all_named": ["a", "b"], "select_top": [["b", .8]]},
                {"all_named": [], "select_top": [["c", .8]]}, {"all_named": ["b"], "select_top": []}]
        out = shadow.report(rows)
        self.assertIn("gate calls 4; named by all 4", out)
        self.assertIn("had them: 2 = 50%", out)
        self.assertRegex(out, r"a\s+named\s+2\s+in select top\s+1 \(50%\)")
        self.assertRegex(out, r"b\s+named\s+2\s+in select top\s+1 \(50%\)")
        self.assertIn("named nothing but select sent something: 1", out)
        self.assertIn("named by all 0", shadow.report([]))


if __name__ == "__main__":
    unittest.main()
