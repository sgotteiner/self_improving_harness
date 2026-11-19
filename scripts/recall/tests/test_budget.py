"""The hook's time budget is checked before every brain call; the pending notes still print when later stages are skipped."""
import io, json, sys, tempfile, time, types, unittest
from unittest import mock

import helpers as h
import brain, ctx, hook


class Budget(unittest.TestCase):
    def tearDown(self):
        ctx.T0 = time.monotonic()

    def slow_brain(self):
        calls = []
        def run(*a, **k):  # every call takes 130 s of the clock
            calls.append(1)
            ctx.T0 -= 130
            return types.SimpleNamespace(stdout=json.dumps({"result": "OK", "usage": {}}))
        return calls, mock.patch.object(brain.subprocess, "run", side_effect=run)

    def test_the_budget_is_checked_before_each_call_not_per_stage(self):
        ctx.T0 = time.monotonic()
        calls, patch = self.slow_brain()
        with patch, mock.patch.object(brain, "LOG", tempfile.mktemp()):
            brain.ask("a"), brain.ask("b")  # started at 0 s and 130 s: allowed
            with self.assertRaises(TimeoutError):
                brain.ask("c")  # would start at 260 s of 300: refused
        self.assertEqual(len(calls), 2)

if __name__ == "__main__":
    unittest.main()
