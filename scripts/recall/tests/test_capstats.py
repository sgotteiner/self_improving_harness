"""cases/stats.json counts per lesson: his verdict on a gate block (his next message, judged by the message step's one call) =
right / wrong / ignored, a recorded correction repeat = missed. The session's own gate settlement counts nothing."""
import json, os, tempfile, unittest
from unittest import mock

import helpers as h
import brain, capowed, capstats, capverdict, capwrite, delegate, index

W = {"situation": "s", "did": "d", "disliked": "x", "lesson_id": "a-case"}


def ZERO(**kw):
    return dict({k: 0 for k in capstats.KEYS}, **kw)


class Capstats(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.d, "cases"))
        open(os.path.join(self.d, "cases", "a-case.md"), "w", encoding="utf-8").write('---\nid: a-case\nlesson: "l"\n---\n')
        for o in (mock.patch.object(index, "CASES", os.path.join(self.d, "cases")), mock.patch.object(capwrite, "PENDING", os.path.join(self.d, "p")),
                  mock.patch.object(capowed, "OWED", os.path.join(self.d, "owed.json")), mock.patch.object(capwrite.history, "record"),
                  mock.patch.object(capverdict, "AWAITING", os.path.join(self.d, "awaiting.json"))):
            o.start()
            self.addCleanup(o.stop)
        self.tp = h.transcript([h.user("x"), h.assistant("y")])

    def stats(self):
        p = os.path.join(self.d, "cases", "stats.json")
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

    def test_session_gate_settlement_counts_nothing_but_a_correction_repeat_is_missed(self):
        self.assertEqual(self.stats(), {})
        capowed.owe("gate", self.tp, lesson="a-case")
        self.assertTrue(capwrite.write(dict(W, source="gate"))[0])
        capowed.owe("gate", self.tp, lesson="a-case")
        self.assertTrue(capwrite.none("false alarm", "gate")[0])
        self.assertEqual(self.stats(), {})
        self.assertTrue(capwrite.write(dict(W, his_words="again"))[0])
        self.assertEqual(self.stats(), {"a-case": ZERO(missed=1)})

    def judge(self, reply):
        """The gate blocked a-case; his next message is judged by a model that answers `reply`."""
        capverdict.block(self.tp, "a-case", "claimed done without a test")
        brain.ask = h.brain_says(reply)
        got = delegate.input_step("ok", self.tp)[0]
        self.assertEqual(capverdict.awaiting(self.tp), [])
        self.assertIn("claimed done without a test", brain.ask.prompts[0])  # the awaiting lesson is in that one call
        return got

    def test_his_verdict_raises_exactly_one_count_and_clears_the_awaiting_entry(self):
        for reply, key in (("TALK\nVERDICT a-case RIGHT", "right"), ("TALK\nVERDICT a-case WRONG", "wrong"),
                           ("TALK\nVERDICT a-case NONE", "ignored"), ("TALK\nNONE", "ignored")):
            os.remove(os.path.join(self.d, "cases", "stats.json")) if self.stats() else None
            self.judge(reply)
            self.assertEqual(self.stats(), {"a-case": ZERO(**{key: 1})}, reply)

    def test_a_failed_model_call_counts_ignored_and_clears(self):
        capverdict.block(self.tp, "a-case", "w")
        brain.ask = mock.Mock(side_effect=RuntimeError("down"))
        with self.assertRaises(RuntimeError):
            delegate.input_step("ok", self.tp)
        self.assertEqual(self.stats(), {"a-case": ZERO(ignored=1)})
        self.assertEqual(capverdict.awaiting(self.tp), [])

    def test_a_neutral_message_after_a_confident_gate_line_is_ignored_and_the_prompt_says_the_line_is_not_evidence(self):
        tp = h.transcript([h.user("x"), h.assistant("done. gate: a-case — claimed done without a test")])
        capverdict.block(tp, "a-case", "claimed done without a test")
        brain.ask = h.brain_says("TALK\nVERDICT a-case NONE")  # the model, told the rule, does not read the claim as his verdict
        delegate.input_step("ok", tp)
        self.assertEqual(self.stats(), {"a-case": ZERO(ignored=1)})
        self.assertIn("not evidence", brain.ask.prompts[0])
        self.assertIn("only when HIS message", brain.ask.prompts[0])

    def test_an_expired_awaiting_entry_counts_ignored_once_and_is_dropped(self):
        json.dump([{"tp": self.tp, "lesson": "a-case", "why": "w", "ts": 1}], open(capverdict.AWAITING, "w", encoding="utf-8"))
        self.assertEqual(capverdict.awaiting(self.tp), [])
        self.assertEqual(capverdict.awaiting(self.tp), [])  # a second load does not count it again
        self.assertEqual(self.stats(), {"a-case": ZERO(ignored=1)})

    def test_old_correct_incorrect_keys_are_dropped_on_the_next_count(self):
        json.dump({"a-case": {"correct": 2, "incorrect": 1, "missed": 3}}, open(os.path.join(self.d, "cases", "stats.json"), "w"))
        capstats.bump("a-case", "right")
        self.assertEqual(self.stats(), {"a-case": ZERO(missed=3, right=1)})

    def test_the_verdict_answer_does_not_disturb_the_flags(self):
        got = self.judge("TALK\nDONE VERDICT a-case RIGHT")
        self.assertEqual(len(got), 2)  # the TALK line and the DONE line

    def test_nothing_counts_for_a_new_lesson_or_a_correction_false_alarm(self):
        self.assertTrue(capwrite.write({"situation": "s", "did": "d", "disliked": "x", "his_words": "w", "lesson": "l2", "slug": "new-one"})[0])
        capowed.owe("correction", self.tp, "p")
        self.assertTrue(capwrite.none("not a mistake")[0])
        self.assertEqual(self.stats(), {})

    def block(self, *ids):
        for i in ids:
            capowed.owe("gate", self.tp, lesson=i)

    def test_block_naming_two_lessons_is_settled_once_each_without_counting(self):
        open(os.path.join(self.d, "cases", "b-case.md"), "w", encoding="utf-8").write('---\nid: b-case\nlesson: "l"\n---\n')
        self.block("a-case", "b-case")
        self.assertTrue(capwrite.write(dict(W, source="gate"))[0])
        self.assertTrue(capwrite.none("false alarm", "gate")[0])
        self.assertEqual(self.stats(), {})
        self.assertEqual(capowed._gates()[0]["settled"], ["a-case", "b-case"])  # still settled once each, for the block-once logic

    def test_write_for_a_lesson_the_block_did_not_name_is_refused(self):
        open(os.path.join(self.d, "cases", "c-case.md"), "w", encoding="utf-8").write('---\nid: c-case\nlesson: "l"\n---\n')
        self.block("a-case", "b-case")
        ok, msg = capwrite.write(dict(W, source="gate", lesson_id="c-case"))
        self.assertFalse(ok)
        self.assertIn("a-case, b-case", msg)
        self.assertEqual(self.stats(), {})
        capwrite.history.record.assert_not_called()

    def test_corrupt_stats_file_is_left_alone(self):
        p = os.path.join(self.d, "cases", "stats.json")
        open(p, "w", encoding="utf-8").write("{broken")
        capowed.owe("gate", self.tp, lesson="a-case")
        self.assertTrue(capwrite.write(dict(W, source="gate"))[0])
        self.assertEqual(open(p, encoding="utf-8").read(), "{broken")

    def test_failed_count_does_not_fail_the_write(self):
        capowed.owe("gate", self.tp, lesson="a-case")
        with mock.patch.object(capwrite.capstats, "bump", side_effect=OSError("boom")):
            self.assertTrue(capwrite.write(dict(W, source="gate"))[0])
        capwrite.history.record.assert_called_once()


if __name__ == "__main__":
    unittest.main()
