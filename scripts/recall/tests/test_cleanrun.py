"""Cleanup upkeep: the merge check gets each lesson with its Right and each alone, reverting a merge brings the archived lessons back,
one open proposal per lesson, one run at a time, a crashed run is logged and retried the next day, the caps, the merge call not repeated."""
import datetime, os, unittest
from unittest import mock

import alllessons, brain, capstats, cleanrules, cleanrun, cleanstate, cleanup, ctx, propapply, proposals, situations
from propbase import Base
from test_cleanup import TODAY, model

class Upkeep(Base):
    """Merge checks, reverting a merge, one run at a time, a crashed run, the caps and the merge call that is not repeated."""
    def setUp(self):
        super().setUp()
        self.s = {l: situations.add(l, "seed", f"sit {l}", date=TODAY) for l in "ab"}

    def merged(self):
        seen = []
        with mock.patch.object(alllessons, "SIZE_LIMIT", 10), mock.patch.object(brain, "ask", model(merge="MERGE a,b | ONE WORDING", seen=seen)):
            cleanup.run_now(TODAY)
        return seen

    def bump(self, lid, key, n):
        for _ in range(n):
            capstats.bump(lid, key)

    def test_the_check_gets_each_lesson_with_its_right_and_each_lesson_is_also_checked_alone(self):
        seen = self.merged()
        check = next(p for t, p in seen if t == "cleanup-check")
        self.assertTrue(all(x in check for x in ("a: L-a Right: R-a", "b: L-b Right: R-b", "two different actions", "ONE WORDING")))
        pairs = [p for t, p in seen if t == "cleanup-pair"]
        self.assertEqual([("R-a" in p, "R-b" in p) for p in pairs], [(True, False), (False, True)])
        self.assertNotIn("too long", next(p for t, p in seen if t == "cleanup-merge"))

    def test_a_merge_one_of_whose_lessons_fails_the_check_alone_is_not_queued(self):
        with mock.patch.object(alllessons, "SIZE_LIMIT", 10), mock.patch.object(brain, "ask", model(merge="MERGE a,b | W", pair="FAIL | b needs another")):
            self.assertEqual(cleanup.run_now(TODAY), [])

    def test_reverting_a_merge_brings_the_archived_lessons_and_their_situations_back(self):
        self.merged()
        row = self.row()
        propapply.apply(row)
        proposals.change(lambda rs: rs[0].update(status="applied", data=row["data"], created="2026-11-01"))
        self.assertFalse(os.path.exists(os.path.join(self.cases, "b.md")))
        self.bump("a", "missed", 2)
        with mock.patch.object(brain, "ask", model()):
            made = cleanup.run_now(TODAY)
        self.assertEqual([k for k, _ in made], ["revert"])
        row = proposals.read()[-1]
        self.assertEqual((row["data"]["restore"], row["data"]["text"]), (["b"], "L-a"))
        propapply.apply(row)
        self.assertEqual((self.lesson("a"), self.lesson("b")), ("L-a", "L-b"))
        self.assertEqual({r["sid"]: r["lesson_id"] for r in situations.read()}, {self.s["a"]: "a", self.s["b"]: "b"})

    def test_one_open_proposal_per_lesson_whatever_its_text(self):
        proposals.queue("edit", "reword lesson a to: other words", {"lesson_id": "a", "text": "other words"})
        self.bump("a", "missed", 3)
        with mock.patch.object(brain, "ask", model()):
            self.assertEqual(cleanup.run_now(TODAY), [])
        self.assertEqual(len(proposals.read()), 1)

    def test_a_second_run_is_refused_while_one_is_on_and_a_stale_claim_is_taken_over(self):
        self.assertTrue(cleanrun.claim(False))
        self.assertFalse(cleanrun.claim(False))
        self.assertFalse(cleanrun.claim(True))
        cleanstate.change(lambda s: s.update(running=s["running"] - cleanrules.RUN_STALE_MIN * 60 - 1))
        self.assertTrue(cleanrun.claim(True))

    def test_a_crashed_run_sets_no_last_run_is_logged_with_its_traceback_and_is_retried_the_next_day(self):
        with mock.patch.object(cleanup, "go", side_effect=RuntimeError("boom")), self.assertRaises(RuntimeError):
            cleanrun.main()
        s = cleanstate.read()
        self.assertEqual(("last_run" in s, "running" in s, s["last_fail"]), (False, False, str(datetime.date.today())))
        self.assertIn("RuntimeError: boom", open(ctx.LOG, encoding="utf-8").read())
        self.assertFalse(cleanrun.due())
        self.assertTrue(cleanrun.due("2099-01-01"))

    def test_a_run_with_a_failing_step_is_a_failure_and_only_a_good_run_sets_last_run(self):
        self.bump("a", "missed", 3)
        with mock.patch.object(brain, "ask", side_effect=RuntimeError("down")):
            cleanrun.main()
        s = cleanstate.read()
        self.assertEqual(("last_run" in s, "last_fail" in s), (False, True))
        cleanstate.change(lambda s: s.pop("last_fail"))
        with mock.patch.object(brain, "ask", model()):
            cleanrun.main()
        s = cleanstate.read()
        self.assertEqual(("last_run" in s, "last_fail" in s), (True, False))

    def test_newkind_notes_are_capped_and_the_oldest_dropped(self):
        for i in range(cleanrules.NEWKIND_KEEP + 3):
            cleanstate.note_new("a", f"case {i}")
        notes = cleanstate.read()["newkind"]["a"]
        self.assertEqual((len(notes), notes[0], notes[-1]), (cleanrules.NEWKIND_KEEP, "case 3", f"case {cleanrules.NEWKIND_KEEP + 2}"))

    def test_the_merge_call_is_not_repeated_until_the_lessons_change(self):
        calls = []
        with mock.patch.object(alllessons, "SIZE_LIMIT", 10), mock.patch.object(brain, "ask", model(seen=calls)):
            cleanup.run_now(TODAY), cleanup.run_now(TODAY)
            self.assertEqual([t for t, _ in calls], ["cleanup-merge"])
            propapply._set_lesson("a", "changed wording")
            cleanup.run_now(TODAY)
        self.assertEqual([t for t, _ in calls], ["cleanup-merge"] * 2)


if __name__ == "__main__":
    unittest.main()
