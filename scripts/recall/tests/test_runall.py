"""scripts/run_all_tests.py: one line per suite, PASSED/FAILED with the failing lines only, and the two paid evals run only when
their files changed since they last passed (or with --eval)."""
import io, os, sys, tempfile, time, unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import run_all_tests as r

PY = [sys.executable, "-I", "-c"]


class RunAll(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp()
        self.watched = os.path.join(d, "watched.py")
        open(self.watched, "w").write("x")
        os.utime(self.watched, (time.time() - 100, time.time() - 100))
        self.stamps = os.path.join(d, "stamps")
        self.suites = [("free", PY + ["print('Ran 3 tests'); print('OK')"], 30, None),
                       ("paid eval", PY + ["print('decisions caught 9/9')"], 30, [self.watched])]
        self.p = [mock.patch.object(r, "SUITES", self.suites), mock.patch.object(r, "stamp", side_effect=lambda n: os.path.join(self.stamps, n + ".stamp"))]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()

    def go(self, force=False):
        out = io.StringIO()
        with mock.patch.object(sys, "stdout", out):
            code = r.main(force)
        return code, out.getvalue().splitlines()

    def test_the_paid_eval_runs_once_then_is_skipped_until_its_files_change(self):
        code, lines = self.go()
        self.assertEqual((code, lines[-1]), (0, "PASSED"))
        self.assertTrue(lines[1].startswith("PASS  paid eval"), lines)
        code, lines = self.go()
        self.assertEqual(lines[1], "SKIP  paid eval: skipped (unchanged)")
        os.utime(self.watched, None)  # the measured file changed after the last pass
        self.assertTrue(self.go()[1][1].startswith("PASS  paid eval"))
        self.assertEqual(self.go()[1][1], "SKIP  paid eval: skipped (unchanged)")
        self.assertTrue(self.go(force=True)[1][1].startswith("PASS  paid eval"))  # --eval

    def test_a_failing_suite_shows_only_its_failing_lines(self):
        self.suites[0] = ("free", PY + ["print('ok line'); print('FAIL: test_a'); print('AssertionError: x'); print('noise'); raise SystemExit(1)"], 30, None)
        code, lines = self.go()
        self.assertEqual(code, 1)
        self.assertIn("FAILED", lines)
        shown = lines[lines.index("FAILED") + 1:]
        self.assertTrue(any("FAIL: test_a" in l for l in shown) and not any("noise" in l for l in shown), shown)

    def test_a_failed_paid_eval_is_not_stamped(self):
        self.suites[1] = ("paid eval", PY + ["print('BAD want=False got=True'); raise SystemExit(1)"], 30, [self.watched])
        self.assertEqual(self.go()[0], 1)
        self.assertEqual(self.go()[0], 1)  # not skipped next time: it never passed


if __name__ == "__main__":
    unittest.main()
