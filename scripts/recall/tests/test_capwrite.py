"""The session writes the case, not the cheap model: detection yields an instruction and no draft call; `write` validates and
runs the privacy scan; clean.py never asks to infer; the gate blocks once on an unpaid write; a session-written occurrence
reaches cases/history as written."""
import json, os, tempfile, unittest
from unittest import mock

import helpers as h
import brain, capowed, capture, capwrite, clean, embed, history, index

GOOD = {"situation": "refactoring a script, he asked for a test", "did": "skipped it", "disliked": "(not stated)",
        "his_words": "I told you to test", "lesson": "run a test", "slug": "run-a-test"}


class Capwrite(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        for o in (mock.patch.object(capwrite, "PENDING", os.path.join(self.d, "p")), mock.patch.object(capowed, "OWED", os.path.join(self.d, "owed.json")),
                  mock.patch.object(capwrite.history, "record"), mock.patch.object(capwrite.pending, "TODO", os.path.join(self.d, "todo.md")),
                  mock.patch.object(embed, "scores", return_value={})):
            o.start()
            self.addCleanup(o.stop)

    def test_a_detected_correction_gives_the_instruction_and_no_draft_call(self):
        tags = []
        brain.ask = lambda p, system="", tag="": (tags.append(tag), ("YES | skipped the test", 1))[1]
        out = capture.process("I told you to test", h.transcript([h.user("x"), h.assistant("did it")]))
        self.assertEqual(tags, ["capture-detect"])
        self.assertIn("capture.py write", out)
        self.assertIn("detector's guess", out)

    def test_write_needs_every_part_accepts_not_stated_and_refuses_a_privacy_hit(self):
        self.assertFalse(capwrite.write({k: v for k, v in GOOD.items() if k != "did"})[0])
        self.assertFalse(capwrite.write(dict(GOOD, disliked=" "))[0])
        self.assertTrue(capwrite.write(GOOD)[0])
        self.assertTrue(os.path.exists(os.path.join(self.d, "p", "run-a-test.md")))
        ok, msg = capwrite.write(dict(GOOD, did="edited C:\\work\\a.py"))
        self.assertFalse(ok)
        self.assertIn("privacy", msg)

    def test_clean_prompt_does_not_tell_the_brain_to_infer(self):
        self.assertNotIn("infer", clean.PROMPT)
        self.assertIn("(not stated)", clean.PROMPT)

    def test_the_gate_blocks_once_on_an_unpaid_write_and_only_for_its_own_message(self):
        tp = h.transcript([h.user("x"), h.assistant("done")])
        capwrite.instruction("why", tp, "x")
        self.assertIn("capture.py write", capowed.settle(tp, False))
        self.assertIsNone(capowed.settle(tp, False))  # once
        capwrite.instruction("why", tp, "x")
        self.assertTrue(capwrite.none("the detector was wrong")[0])  # settled as not a mistake
        self.assertIsNone(capowed.settle(tp, False))
        capwrite.instruction("why", tp, "x")
        later = h.transcript([h.user("x"), h.assistant("done"), h.user("another message"), h.assistant("ok")])
        self.assertIsNone(capowed.settle(later, False))  # an earlier message never blocks a later one

    def test_a_write_before_a_background_notice_restart_still_counts(self):
        tp = h.transcript([h.user("x"), h.assistant("noted"), h.notice("t1", "toolu_a"), h.assistant("agent returned")])
        capwrite.instruction("why", tp, "x")
        self.assertTrue(capwrite.write(GOOD)[0])  # paid in the turn before the restart
        self.assertIsNone(capowed.settle(tp, False))

    def test_a_session_written_occurrence_reaches_cases_history_as_written(self):
        cases = os.path.join(self.d, "cases")
        os.makedirs(cases)
        open(os.path.join(cases, "a-case.md"), "w", encoding="utf-8").write('---\nid: a-case\nlesson: "l"\n---\n')
        c = {"situation": "S-as-written", "assistant_did": "D-as-written", "disliked": "L-as-written"}
        with mock.patch.object(history, "DB", os.path.join(self.d, "h.db")), mock.patch.object(history, "OUT", os.path.join(cases, "history")), \
                mock.patch.object(index, "CASES", cases), mock.patch.object(history, "spawn_sync"), mock.patch.object(embed, "encode"), \
                mock.patch.object(clean, "clean", side_effect=AssertionError("no Haiku rewrite")):
            history.add("a-case", "correction", "raw words", clean_text=json.dumps(c))
            history.sync()
        out = open(os.path.join(cases, "history", "a-case.md"), encoding="utf-8").read()
        self.assertTrue(all(x in out for x in c.values()), out)


if __name__ == "__main__":
    unittest.main()
