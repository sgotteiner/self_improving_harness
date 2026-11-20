"""Patch before create: a repeat of an approved lesson becomes a wording edit with its situation attached (proposed, never
orphaned), the session's words are recorded, the model's wording passes the privacy scan; anything else is a new-lesson proposal."""
import sqlite3, unittest
from unittest import mock

import brain, capwrite, history, patchfirst, pending, proposals, situations
from propbase import Base, GOOD


class PatchFirst(Base):
    def cmp(self, reply, **kw):
        with mock.patch.object(brain, "ask", return_value=(reply, 1)):
            return capwrite.write(dict(GOOD, **kw))[1]

    def test_the_same_kind_of_mistake_becomes_a_wording_edit_with_its_situation_attached_not_yet_active(self):
        msg = self.cmp("SAME a | One general sentence.")
        self.assertIn("repeats the lesson a", msg)
        (r,) = proposals.read()
        self.assertEqual((r["kind"], r["data"]["lesson_id"], r["data"]["text"]), ("edit", "a", "One general sentence."))
        self.assertEqual([(s["lesson_id"], s["status"]) for s in situations.read()], [("a", "proposed")])
        self.assertEqual(self.lesson(), "L-a")

    def test_his_words_are_recorded_in_history_as_for_any_repeat_and_linked_to_the_situation(self):
        self.cmp("SAME a | One general sentence.")
        (row,) = sqlite3.connect(history.DB).execute("SELECT id, case_id, source, text FROM occurrence").fetchall()
        self.assertEqual(row[1:], ("a", "correction", "test it first"))
        self.assertEqual(situations.read()[0]["occ"], row[0])

    def test_a_proposal_that_was_not_queued_leaves_no_proposed_situation(self):
        for failure in ({"return_value": None}, {"side_effect": OSError("locked")}):
            with mock.patch.object(proposals, "queue", **failure):
                self.cmp("SAME a | One general sentence.", slug="s" + str(len(failure)))
            self.assertNotIn("proposed", [s["status"] for s in situations.read()])
        self.assertEqual([s["status"] for s in situations.read()], ["retired", "retired"])

    def test_a_reworded_lesson_with_a_private_path_is_not_proposed_as_an_edit(self):
        self.cmp(r"SAME a | Edit C:\work\private\a.py first.")
        self.assertEqual([r["kind"] for r in proposals.read()], ["new-lesson"])
        self.assertEqual(situations.read(), [])

    def test_compare_reads_the_one_line_answer_and_sends_every_lesson(self):
        with mock.patch.object(brain, "ask", return_value=("`SAME b` | W.", 1)) as m:
            self.assertEqual(patchfirst.compare("new lesson text"), ("b", "W."))
        self.assertTrue("a: L-a" in m.call_args[0][0] and "b: L-b" in m.call_args[0][0] and "new lesson text" in m.call_args[0][0])
        self.assertIn("lesson: \"x\"", pending.case_text("s", {"lesson": "x", "situation": "y", "did": "z"}, "raw", "2026-11-20"))

    def test_a_different_kind_an_unknown_id_or_a_failed_call_is_a_new_lesson_proposal(self):
        for reply in ("NEW", "SAME no-such-lesson | x", "garbage"):
            self.cmp(reply)
        with mock.patch.object(brain, "ask", side_effect=OSError("down")):
            capwrite.write(dict(GOOD, slug="other"))
        self.assertEqual([r["kind"] for r in proposals.read()], ["new-lesson"] * 2)  # the first three are one proposal, deduplicated


if __name__ == "__main__":
    unittest.main()
