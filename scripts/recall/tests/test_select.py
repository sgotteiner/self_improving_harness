"""scripts/select_tests.py + run_all_tests.py: a change selects only the suites it needs; --all selects every suite."""
import io, os, sys, unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import run_all_tests as r
import select_tests as s

PY = [sys.executable, "-I", "-c"]


class Select(unittest.TestCase):
    def test_a_recall_module_selects_only_the_test_files_that_import_it(self):
        got = s.select(["scripts/recall/shortreturn.py"])
        self.assertEqual(list(got), ["recall tests"])
        self.assertEqual(got["recall tests"][1], ["test_shortreturn"])

    def test_a_case_file_selects_only_the_capture_check(self):
        self.assertEqual(list(s.select(["cases/x.md"])), ["capture check"])

    def test_gate_decision_and_sdd_code_select_their_suites(self):
        self.assertEqual(list(s.select(["scripts/recall/eval_gate.py"])), ["recall tests", "gate eval", "gate eval (real brain)"])
        self.assertIn("decision eval", s.select(["scripts/recall/decisions.py"]))
        self.assertEqual(list(s.select(["skills/sdd/scripts/x.js", "skills/system-map/y.md"])), ["sdd tests"])

    def test_an_unrelated_file_selects_nothing(self):
        self.assertEqual(s.select(["README.txt", "tasks/todo.md"]), {})

    def test_a_module_no_test_covers_runs_the_whole_recall_suite(self):
        self.assertEqual(s.select(["scripts/recall/replay.py"])["recall tests"][1], [])

    def test_a_changed_test_file_runs_itself(self):
        self.assertEqual(s.select(["scripts/recall/tests/test_flags.py"])["recall tests"][1], ["test_flags"])


class Main(unittest.TestCase):
    def go(self, chosen):
        suites = [("recall tests", PY + ["import sys; print('OK'); print('passed', sys.argv[1:])"], 30, None),
                  ("sdd tests", PY + ["print('Ran 1'); print('OK')"], 30, None)]
        out = io.StringIO()
        with mock.patch.object(r, "SUITES", suites), mock.patch.object(sys, "stdout", out):
            r.main(False, chosen)
        return out.getvalue()

    def test_all_runs_every_suite(self):
        o = self.go(None)
        self.assertTrue("recall tests" in o and "sdd tests" in o and "CHOOSE" not in o, o)

    def test_only_the_chosen_suite_runs_with_its_args_and_a_reason_line(self):
        o = self.go({"recall tests": ("x.py changed", ["test_x"])})
        self.assertIn("CHOOSE  recall tests: x.py changed", o)
        self.assertIn("['test_x']", o)
        self.assertNotIn("sdd tests", o)

    def test_nothing_chosen_says_so(self):
        self.assertIn("nothing to test", self.go({}))


if __name__ == "__main__":
    unittest.main()
