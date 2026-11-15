"""gate.py: the lesson check and the delegation check both run and come in one block; a hedging lesson verdict is dropped."""
import io, json, sys, unittest
from unittest import mock

import ctx, gate


def run(lesson, delegation):
    out = io.StringIO()
    with mock.patch.object(gate, "check", return_value=lesson), mock.patch.object(gate, "delegation", return_value=delegation), \
            mock.patch.object(ctx, "enabled", side_effect=lambda s: s == "output-gate"), mock.patch.object(sys, "stdin", io.StringIO('{"transcript_path": "x"}')), \
            mock.patch.object(sys, "stdout", out):
        gate.main()
    return json.loads(out.getvalue()) if out.getvalue() else None


class Gate(unittest.TestCase):
    def test_both_reasons_in_one_block(self):
        got = run(("some-case", "no run shown"), "Delegation gate: call the reviewer")
        self.assertEqual(got["decision"], "block")
        self.assertIn("cases/some-case.md", got["reason"])
        self.assertIn("call the reviewer", got["reason"])

    def test_one_reason_alone(self):
        self.assertIn("call the reviewer", run(None, "Delegation gate: call the reviewer")["reason"])
        self.assertIn("no run shown", run(("c", "no run shown"), None)["reason"])
        self.assertIsNone(run(None, None))

    def test_a_lesson_verdict_that_leads_with_a_hedge_does_not_block(self):
        self.assertIsNone(run(("c", "This may be OK: it claims it works"), None))
        self.assertIsNotNone(run(("c", "Claims it works with no run; unclear which file, run the test"), None))


if __name__ == "__main__":
    unittest.main()
