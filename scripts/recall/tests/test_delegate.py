"""The message step (delegate.input_step) and the prompt sources it reads at run time."""
import os, tempfile, unittest
from unittest import mock

import helpers as h
import brain, delegate


class InputAndSources(unittest.TestCase):
    def test_the_intent_step_prints_the_instruction_for_his_kind_of_message(self):
        def say(prev, prompt, word):
            brain.ask = h.brain_says(word)
            tp = h.transcript([h.user("x"), h.assistant(prev), h.user(prompt)])
            return delegate.input_step(prompt, tp)[0], brain.ask
        got, ask = say("Done.", "is the retry covered?", "QUESTION-YESNO")
        self.assertEqual(len(got), 1)
        self.assertIn("start with yes or no", got[0])
        got, ask = say("Done.", "add a retry to the payment", "TASK")
        self.assertIn("say back what he asked", got[0])
        self.assertIn("run it only after his yes", got[1])  # tests are proposed, not run
        got, ask = say("I will add a retry so a failed payment is not lost. OK?", "yes", "CONFIRMATION")
        self.assertIn("delegate it to the implementer", got[0])
        self.assertIn("I will add a retry", ask.prompts[0])  # the previous full assistant reply is in the prompt
        self.assertEqual(say("x", "hmm", "garbage words")[0], [])  # an unknown answer prints nothing

    def test_capture_check_fails_on_a_bad_source(self):
        import casesave, index
        with mock.patch.object(delegate, "check_sources", return_value=["boom"]), mock.patch.object(index, "case_files", return_value=[]):
            self.assertFalse(casesave.check_all())

    def test_renamed_headings_fail_loudly(self):
        self.assertEqual(delegate.check_sources(), [])
        d = tempfile.mkdtemp()
        a, b = os.path.join(d, "CLAUDE.md"), os.path.join(d, "draft.md")
        open(a, "w").write("## Core rules\nx\n## Next\n")
        open(b, "w").write(open(delegate.DRAFT, encoding="utf-8").read().replace("## Output step", "## Output stage"))
        old = delegate.CLAUDE_MD, delegate.DRAFT
        delegate.CLAUDE_MD, delegate.DRAFT = a, b
        try:
            bad = delegate.check_sources()
        finally:
            delegate.CLAUDE_MD, delegate.DRAFT = old
        self.assertTrue(any("The core" in p for p in bad) and any("Output step" in p for p in bad), bad)


if __name__ == "__main__":
    unittest.main()
