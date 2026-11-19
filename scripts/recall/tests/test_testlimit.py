"""Test-limit approval: his yes counts only when the assistant's previous reply asked whether to continue a cut test."""
import os, sys, tempfile, unittest
from unittest import mock

import helpers as h

sys.path.insert(0, os.path.join(h.RECALL, ".."))
import testlimit

SLOT = {"enabled": True, "seconds": 60}


class Approval(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp()
        self.stopped, self.ok = os.path.join(d, "stopped"), os.path.join(d, "ok")
        open(self.stopped, "w").write("abc123\n1\n")
        for o in (mock.patch.object(testlimit, "STOPPED_FILE", self.stopped), mock.patch.object(testlimit, "APPROVED_FILE", self.ok)):
            o.start()
            self.addCleanup(o.stop)

    def yes(self, reply):
        tp = h.transcript([h.user("run it"), h.assistant(reply), h.user("yes")])
        return testlimit.prompt({"prompt": "yes", "transcript_path": tp}, SLOT)

    def test_a_yes_is_ignored_when_the_previous_reply_did_not_ask_about_a_test(self):
        self.assertIsNone(self.yes("I will rename the helper so the name says what it does. OK?"))
        self.assertFalse(os.path.exists(self.ok))
        self.assertTrue(os.path.exists(self.stopped), "the cut run stays recorded for the real question")

    def test_a_yes_to_the_continue_question_approves_the_cut_command(self):
        self.assertIn("approved continuing", self.yes("The test run was cut at 60 s; it had finished 3 of 5 files. Continue?"))
        self.assertTrue(os.path.exists(self.ok))


if __name__ == "__main__":
    unittest.main()
