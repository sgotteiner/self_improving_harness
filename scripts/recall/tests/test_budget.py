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

    def test_the_draft_line_prints_even_when_every_brain_stage_is_skipped(self):
        ctx.T0 = time.monotonic() - 1000
        tp = h.transcript([h.user("x"), h.assistant("I propose A or B.")])
        out, order = io.StringIO(), []
        import drafts, setupstate
        with mock.patch.object(ctx, "enabled", side_effect=lambda s: s in ("capture", "decision-capture", "recall-hook", "delegation-hook")), \
                mock.patch.object(drafts, "daily_line", side_effect=lambda: order.append("drafts") or ["DRAFTS-LINE"]), \
                mock.patch.object(setupstate, "save_snapshot", side_effect=lambda tp: order.append("snapshot")), \
                mock.patch.object(brain.subprocess, "run") as run, \
                mock.patch.object(sys, "stdin", io.StringIO(json.dumps({"prompt": "go with option a please", "transcript_path": tp}))), \
                mock.patch.object(sys, "stdout", out):
            hook.main()
        run.assert_not_called()
        self.assertIn("DRAFTS-LINE", out.getvalue())
        self.assertEqual(order, ["snapshot", "drafts"], "the snapshot is taken first, before any slow stage")


if __name__ == "__main__":
    unittest.main()
