"""When a proposal counts as shown and who answers it: only if the session's reply had the line, only in that session, one
outstanding at a time, a failed call keeps it, the switches that read his yes, and a failed apply never leaves a situation proposed."""
import json, os, time, unittest
from unittest import mock

import capstats, ctx, propapply, proposals, situations
from propbase import Base, TODAY, shown

EDIT = ("edit", "reword lesson a to: W", {"lesson_id": "a", "text": "W"})
PLAIN = "Fixed it. Want me to run the other check too?"


class Seen(Base):
    def test_a_reply_without_the_line_is_not_shown_and_his_yes_does_not_apply_it(self):
        self.offer(*EDIT)
        self.ask("TASK\nPROPOSAL p0001 YES", PLAIN)
        self.assertNotIn("PROPOSAL", self.prompt)  # nothing was shown, so the call is not asked about it
        self.assertEqual((self.row()["status"], self.lesson()), ("queued", "L-a"))  # back in the queue, not dropped

    def test_only_his_next_message_in_that_session_answers_it(self):
        self.offer(*EDIT)
        self.ask("TASK\nPROPOSAL p0001 YES", shown(EDIT[1]), tp="other-session")
        self.assertEqual((self.row()["status"], self.lesson()), ("offered", "L-a"))  # another session neither shows nor answers it
        self.ask("TASK\nPROPOSAL p0001 YES", shown(EDIT[1]))
        self.assertEqual((self.row()["status"], self.lesson()), ("applied", "W"))

    def test_a_failed_model_call_keeps_it_waiting_for_the_next_message(self):
        self.offer(*EDIT)
        with self.assertRaises(RuntimeError):
            self.ask(RuntimeError("down"), shown(EDIT[1]))
        self.assertEqual((self.row()["status"], self.lesson()), ("shown", "L-a"))
        self.ask("TASK\nPROPOSAL p0001 YES", PLAIN)  # the line is not in this reply any more: it stays shown
        self.assertEqual((self.row()["status"], self.lesson()), ("applied", "W"))

    def test_one_outstanding_at_a_time_even_on_the_next_day(self):
        proposals.queue(*EDIT)
        proposals.queue("retire-lesson", "retire lesson b", {"lesson_id": "b"})
        self.assertIn("reword lesson a", proposals.line("tp", TODAY))
        self.assertEqual(proposals.line("tp", "2999-01-01"), "")  # offered, not answered
        self.ask("TASK", shown(EDIT[1]))
        self.assertIn("retire lesson b", proposals.line("tp", "2999-01-01"))

    def test_the_question_in_the_reply_is_told_apart_from_the_proposal_in_the_prompt(self):
        self.offer(*EDIT)
        self.ask("TASK", shown(EDIT[1]))
        self.assertIn("A yes to anything else in the reply", self.prompt)

    def test_nothing_is_shown_when_his_yes_could_not_be_read_and_it_is_logged_once(self):
        proposals.queue(*EDIT)
        for off in ("delegation-hook", "capture"):
            with mock.patch.object(ctx, "enabled", side_effect=lambda s: s != off), mock.patch.object(ctx, "log") as log:
                self.assertEqual((proposals.line("tp", TODAY), proposals.line("tp", TODAY)), ("", ""))
            self.assertEqual(log.call_count, 1)
            os.remove(proposals.OFF_MARK)
        self.assertEqual(self.row()["status"], "queued")

    def age(self):
        rows = proposals.read()
        rows[0]["at"] = time.time() - proposals.DAY - 1
        open(proposals.path(), "w", encoding="utf-8").write(json.dumps(rows[0]) + "\n")

    def test_an_offer_nobody_answered_goes_back_to_the_queue(self):
        self.offer(*EDIT)
        self.age()
        self.assertIn("reword lesson a", proposals.line("elsewhere", "2999-01-01"))  # back in the queue, offered to the next session
        self.assertEqual(self.row()["tp"], "elsewhere")

    def test_a_shown_one_nobody_answered_is_dropped_with_its_situation(self):
        sid = situations.add("a", "gate", "s", status=situations.PROPOSED)
        self.offer("edit", "reword lesson a to: W", {"lesson_id": "a", "text": "W", "sids": [sid]})
        with self.assertRaises(RuntimeError):
            self.ask(RuntimeError("down"), shown(EDIT[1]))
        self.age()
        proposals.line("tp", "2999-01-01")
        self.assertEqual((self.row()["status"], situations.read()[0]["status"]), ("dropped", "retired"))


class FailedApply(Base):
    def test_a_failed_apply_is_closed_as_failed_and_its_situation_is_retired(self):
        sid = situations.add("a", "gate", "s", status=situations.PROPOSED)
        self.offer("edit", "reword lesson a to: bad", {"lesson_id": "a", "text": r"see C:\work\private\a.py", "sids": [sid]})
        self.ask("TASK\nPROPOSAL p0001 YES", shown("reword lesson a to: bad"))
        self.assertEqual((self.row()["status"], self.lesson(), situations.read()[0]["status"]), ("failed", "L-a", "retired"))

    def test_a_merge_that_fails_midway_puts_every_file_and_its_stats_back(self):
        capstats.bump("b", "wrong")
        situations.add("b", "gate", "from b")
        before = {c: open(os.path.join(self.cases, c + ".md"), encoding="utf-8").read() for c in "ab"}
        with mock.patch.object(situations, "relink", side_effect=OSError("locked")):
            with self.assertRaises(OSError):
                propapply.apply({"kind": "merge", "data": {"into": "a", "from": ["b"], "text": "MERGED"}})
        self.assertEqual({c: open(os.path.join(self.cases, c + ".md"), encoding="utf-8").read() for c in "ab"}, before)
        self.assertEqual(os.listdir(os.path.join(self.cases, "_archive")), [])
        self.assertEqual(json.load(open(os.path.join(self.cases, "stats.json")))["b"]["wrong"], 1)
        self.assertEqual([r["lesson_id"] for r in situations.read()], ["b"])
        with self.assertRaises(FileNotFoundError):  # a lesson that is not there stops it before anything changed
            propapply.apply({"kind": "merge", "data": {"into": "a", "from": ["nope"], "text": "M"}})
        self.assertEqual(self.lesson(), "L-a")


if __name__ == "__main__":
    unittest.main()
