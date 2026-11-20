"""Learning from the work: a struggle with its fix gives one draft that becomes a proposal (never a lesson), a plain stretch gives NONE,
a private draft is dropped, DONE and the 10-turn count each start exactly one detached run, only one at a time."""
import json, os, unittest
from unittest import mock

import brain, ctx, history, proposals, situations, workreview as w
import helpers as h
from propbase import Base

DRAFT = ("SITUATION: fixing a failing build\nDID: retried the same command without reading the error\n"
         "OUTCOME: reading the error first showed the real cause and the fix worked\nLESSON: Read the error before retrying.\nSLUG: read-error-first")


def struggle():
    t1, t2 = h.tool("Bash", {"command": "make"}), h.tool("Bash", {"command": "make"})
    return [h.user("fix the build"), h.assistant(t1), h.result(t1["id"], "Error: missing flag"), h.assistant("retrying", t2),
            h.result(t2["id"], "Error: missing flag"), h.user("read the error"), h.assistant("the flag was missing, fixed")]


class Work(Base):
    def setUp(self):
        super().setUp()
        for p in (mock.patch.dict(os.environ, {"RECALL_WORK_STATE": os.path.join(self.d, "w.json")}),
                  mock.patch.object(ctx, "enabled", return_value=True)):
            p.start()
            self.addCleanup(p.stop)

    def run_review(self, entries, reply, same="NEW"):
        tp = h.transcript(entries)
        with mock.patch.object(brain, "ask", side_effect=lambda p, system="", tag="": (same if tag == "patch-first" else reply, 1)):
            return tp, w.run(tp)

    def test_a_struggle_and_its_fix_gives_one_draft_that_is_a_new_lesson_proposal_only(self):
        tp, d = self.run_review(struggle(), DRAFT)
        self.assertEqual(d["SLUG"], "read-error-first")
        (r,) = proposals.read()
        self.assertEqual((r["kind"], r["data"]["source"], r["data"]["slug"]), ("new-lesson", "work", "read-error-first"))
        self.assertFalse(os.path.exists(os.path.join(self.cases, "read-error-first.md")))  # only his yes adds it

    def test_the_draft_that_repeats_a_lesson_is_an_edit_proposal_with_a_work_situation(self):
        self.run_review(struggle(), DRAFT, same="SAME a | Read the error first.")
        (r,) = proposals.read()
        self.assertEqual((r["kind"], r["data"]["lesson_id"]), ("edit", "a"))
        self.assertEqual([(s["source"], s["status"]) for s in situations.read()], [("work", "proposed")])

    def test_a_plain_stretch_gives_none_and_queues_nothing(self):
        tp, d = self.run_review([h.user("hello"), h.assistant("hi")], "NONE")
        self.assertIsNone(d)
        self.assertEqual(proposals.read(), [])

    def test_a_draft_with_a_private_path_is_dropped(self):
        _, d = self.run_review(struggle(), DRAFT.replace("a failing build", r"C:\work\private\build.py"))
        self.assertIsNone(d)
        self.assertEqual(proposals.read(), [])

    def test_a_failed_call_is_logged_the_stretch_is_marked_reviewed_and_the_run_is_released(self):
        tp = h.transcript(struggle())
        with mock.patch.object(brain, "ask", side_effect=OSError("down")):
            self.assertIsNone(w.run(tp))
        self.assertEqual(w.read()[tp]["humans"], 2)
        self.assertEqual(w.stretch(tp, w.read()[tp]["entries"]), "")
        self.assertNotIn("running", w.read())

    def test_done_starts_exactly_one_run_and_a_second_start_while_it_runs_starts_none(self):
        tp = h.transcript([h.user("a"), h.assistant("b")])
        with mock.patch.object(w.subprocess, "Popen") as p:
            self.assertTrue(w.start(tp, True))
            self.assertFalse(w.start(tp, True))
        self.assertEqual(p.call_count, 1)

    def test_ten_human_turns_since_the_last_review_start_one_run_nine_start_none(self):
        es = [e for i in range(w.LEARN_TURNS - 1) for e in (h.user(f"m{i}"), h.assistant("ok"))]
        with mock.patch.object(w.subprocess, "Popen") as p:
            self.assertFalse(w.start(h.transcript(es), False))
            tp = h.transcript(es + [h.user("tenth")])
            self.assertTrue(w.start(tp, False))
            w.change(lambda s: s.update({tp: {"entries": 0, "humans": w.LEARN_TURNS}, "running": 0}))  # that run has finished
            self.assertFalse(w.start(tp, False))  # counted from the last review
        self.assertEqual(p.call_count, 1)

    def test_the_stretch_is_cut_before_the_call_so_work_that_comes_in_during_it_is_not_marked_reviewed(self):
        tp = h.transcript(struggle())
        def ask(p, system="", tag=""):
            open(tp, "a", encoding="utf-8").write(json.dumps(h.user("one more thing")) + "\n")  # arrives during the call
            return "NONE", 1
        with mock.patch.object(brain, "ask", side_effect=ask):
            w.run(tp)
        self.assertEqual(w.read()[tp]["entries"], len(struggle()))
        self.assertIn("one more thing", w.stretch(tp, w.read()[tp]["entries"]))

    def run_none(self, tp):
        with mock.patch.object(brain, "ask", return_value=("NONE", 1)) as a:
            w.run(tp)
        return a

    def test_a_stretch_in_which_capture_recorded_an_occurrence_is_skipped_without_a_call_but_work_rows_do_not_count(self):
        tp = h.transcript(struggle())
        w.start(tp, False)  # the first message of the session: the marks the stretch is measured from
        history.add("a", "work", "his words")
        self.assertEqual(self.run_none(tp).call_count, 1)  # a work row is not capture's
        history.add("a", "correction", "his words")
        w.change(lambda s: s[tp].update(entries=0))  # a new stretch to review
        self.run_none(tp).assert_not_called()

    def test_a_new_lesson_proposal_from_capture_in_the_stretch_skips_it_too(self):
        tp = h.transcript(struggle())
        w.start(tp, False)
        proposals.queue("new-lesson", "add x", {"source": "gate", "slug": "x"})
        self.run_none(tp).assert_not_called()

    def test_a_tool_result_with_a_private_path_never_reaches_the_brain_and_a_private_line_is_redacted(self):
        t = h.tool("Bash", {"command": "make"})
        es = [h.user("fix it, mail me at a@b.com"), h.assistant(t), h.result(t["id"], r"Error in C:\work\private\x.py line 3"),
              h.assistant("fixed")]
        p = self.run_none(h.transcript(es)).call_args[0][0]
        self.assertNotIn("private", p)
        self.assertNotIn("a@b.com", p)
        self.assertIn("O: (redacted)", p)
        self.assertIn("A: fixed", p)

    def test_a_busy_lock_is_retried_and_then_running_is_cleared_anyway(self):
        tp = h.transcript(struggle())
        w.change(lambda s: s.update({"running": 123}))
        real, n = w.change, [0]
        def busy(fn):
            n[0] += 1
            if n[0] <= w.RETRIES - 1:
                raise OSError("locked")
            return real(fn)
        with mock.patch.object(w, "change", busy), mock.patch.object(w.time, "sleep"):
            self.run_none(tp)
        self.assertNotIn("running", w.read())
        w.change(lambda s: s.update({"running": 123}))
        with mock.patch.object(w, "change", side_effect=OSError("locked")), mock.patch.object(w.time, "sleep"):
            self.run_none(tp)  # never gets the lock: written without it
        self.assertNotIn("running", w.read())

    def test_a_done_that_finds_a_review_running_is_remembered_and_run_after_it(self):
        tp = h.transcript(struggle())
        with mock.patch.object(w.subprocess, "Popen") as p:
            self.assertTrue(w.start(tp, True))
            self.assertFalse(w.start(tp, True))  # running: remembered
            self.assertEqual(p.call_count, 1)
            self.run_none(tp)  # the first review ends
            self.assertEqual(p.call_count, 2)  # the remembered DONE runs now
            self.assertIn("running", w.read())  # claimed for it
            self.assertNotIn("again", w.read())

    def test_off_starts_nothing(self):
        with mock.patch.object(ctx, "enabled", return_value=False), mock.patch.object(w.subprocess, "Popen") as p:
            self.assertFalse(w.start(h.transcript([h.user("a")]), True))
        p.assert_not_called()


if __name__ == "__main__":
    unittest.main()
