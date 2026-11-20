"""The proposal queue: offered one a day, his yes (read by the message step's one call) applies it, anything else drops it;
retiring archives with stats; a merge relinks the situations; the hook prints the line."""
import io, json, os, sys, unittest
from unittest import mock

import helpers as h
import brain, capstats, capverdict, casesave, ctx, delegate, history, hook, index, propapply, proposals, situations
from propbase import Base, GOOD, TODAY, shown


class Queue(Base):
    def test_a_queued_proposal_is_offered_once_and_only_one_a_day(self):
        proposals.queue("retire-lesson", "retire lesson b", {"lesson_id": "b"})
        proposals.queue("retire-lesson", "retire lesson a", {"lesson_id": "a"})
        self.assertIsNone(proposals.queue("retire-lesson", "retire lesson a", {"lesson_id": "a"}))  # already open
        self.assertIn("proposal: retire lesson b — yes / ignore", proposals.line("tp", TODAY))
        self.assertEqual(proposals.line("tp", TODAY), "")  # one is outstanding
        self.assertEqual(self.ask("TASK", shown("retire lesson b")), "TASK")  # his next message answers nothing: dropped
        self.assertEqual(proposals.line("tp", TODAY), "")  # still the same day: the second one waits
        self.assertIn("retire lesson a", proposals.line("tp", "2999-01-01"))
        self.ask("TASK", shown("retire lesson a"))
        self.assertEqual(proposals.line("tp", "2999-01-02"), "")  # a settled one is never offered again

    def test_yes_applies_and_the_answer_is_read_by_the_same_call_without_changing_the_reply(self):
        sid = situations.add("a", "gate", "same mistake again", "d", "o", status=situations.PROPOSED)
        self.offer("edit", "reword lesson a to: NEW WORDS", {"lesson_id": "a", "text": "NEW WORDS", "sids": [sid]})
        out = self.ask("TASK\nPROPOSAL p0001 YES", shown("reword lesson a to: NEW WORDS"))
        self.assertIn("`PROPOSAL p0001 YES`", self.prompt)  # the one call is asked about his yes
        self.assertIn("proposal: reword lesson a to: NEW WORDS", self.prompt)
        self.assertEqual(out.strip(), "TASK")
        self.assertEqual((self.lesson(), self.row()["status"], situations.read()[0]["status"]), ("NEW WORDS", "applied", "active"))
        self.assertEqual(index.parse(os.path.join(self.cases, "a.md"))["right"], "R-a")  # the rest of the file is untouched

    def test_any_other_reply_drops_it_and_retires_its_situation(self):
        for n, reply in enumerate(("TASK\nPROPOSAL p0001 NO", "TASK\nok"), 1):
            sid = situations.add("a", "gate", f"x{n}", status=situations.PROPOSED)
            pid = self.offer("edit", f"reword a to: W{n}", {"lesson_id": "a", "text": f"W{n}", "sids": [sid]}, today=f"2999-01-0{n}")
            self.ask(reply, shown(f"reword a to: W{n}"))
            self.assertEqual((self.lesson(), self.row(pid)["status"], situations.read()[-1]["status"]), ("L-a", "dropped", "retired"))

    def test_retiring_a_lesson_moves_it_to_the_archive_with_its_stats_and_keeps_its_situations(self):
        capstats.bump("b", "wrong")
        situations.add("b", "gate", "kept", "d", "o")
        self.offer("retire-lesson", "retire lesson b", {"lesson_id": "b"})
        self.ask("TASK\nPROPOSAL p0001 YES", shown("retire lesson b"))
        arch = os.path.join(self.cases, "_archive")
        self.assertEqual(sorted(os.listdir(arch)), ["b.md", "b.stats.json"])
        self.assertEqual(json.load(open(os.path.join(arch, "b.stats.json")))["wrong"], 1)
        self.assertNotIn("b", json.load(open(os.path.join(self.cases, "stats.json"))))
        self.assertFalse(os.path.exists(os.path.join(self.cases, "b.md")))
        self.assertEqual([r["situation"] for r in situations.read()], ["kept"])

    def test_a_merge_relinks_the_situations_and_a_retired_situation_stays_in_the_store(self):
        situations.add("b", "gate", "from b", "d", "o")
        sid = situations.add("a", "gate", "old", "d", "o")
        propapply.apply({"kind": "merge", "data": {"into": "a", "from": ["b"], "text": "MERGED"}})
        propapply.apply({"kind": "retire-situation", "data": {"sid": sid}})
        self.assertEqual((self.lesson(), [(r["lesson_id"], r["status"]) for r in situations.read()]),
                         ("MERGED", [("a", "active"), ("a", "retired")]))
        self.assertTrue(os.path.exists(os.path.join(self.cases, "_archive", "b.md")))

    def test_a_new_lesson_goes_through_approve_and_a_broken_queue_never_raises(self):
        d = dict(GOOD, did="said fixed", source="correction")
        with mock.patch.object(casesave, "approve", return_value=True) as ap, mock.patch.object(history, "record") as rec:
            propapply.apply({"kind": "new-lesson", "data": dict(d, slug="show-output", his_words="raw")})
        ap.assert_called_once_with("show-output", propapply.NEW_LEVEL)
        self.assertIn("lesson: \"show the output", open(os.path.join(self.cases, "_pending", "show-output.md"), encoding="utf-8").read())
        rec.assert_called_once()
        open(proposals.path(), "w").write("not json\n")
        self.assertEqual(proposals.line("tp"), "")

    def test_the_hook_prints_the_days_proposal_line_after_the_kind_line(self):
        proposals.queue("retire-lesson", "retire lesson b", {"lesson_id": "b"})
        out, tp = io.StringIO(), h.transcript([h.user("x"), h.assistant("ok")])
        for _ in (1, 2):  # the second message of the same day gets none
            with mock.patch.object(delegate, "input_step", return_value=(["TASK line"], 5)), mock.patch.object(sys, "stdout", out), \
                    mock.patch.object(sys, "stdin", io.StringIO(json.dumps({"prompt": "do the thing now", "transcript_path": tp}))), \
                    mock.patch.dict(os.environ, {"RECALL_HOOK": "1"}), \
                    mock.patch.object(ctx, "enabled", side_effect=lambda s: s in ("delegation-hook", "capture")):
                hook.main()
        lines = out.getvalue().splitlines()
        self.assertEqual((lines[0], len(lines)), ("TASK line", 3))
        self.assertIn("proposal: retire lesson b", lines[1])
        self.assertEqual(lines[2], "TASK line")


if __name__ == "__main__":
    unittest.main()
