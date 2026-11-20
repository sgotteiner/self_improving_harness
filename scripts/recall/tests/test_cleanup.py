"""Cleanup proposals on a fixture store (lessons a and b): each rule queues exactly its proposal and nothing else, a merge keeps
every active situation linked, a failing draft is not queued, one proposal per lesson, and an edit after which `missed` rises is
offered back. The model is mocked by the tag of the call."""
import unittest
from unittest import mock

import alllessons, brain, capstats, cleanrun, cleanstate, cleanup, propapply, proposals, situations
from propbase import Base

OLD = "2026-01-01"
TODAY = "2026-11-20"


def model(reword="NEW WORDS", check="OK", merge="NONE", pair="OK", seen=None):
    def ask(prompt, system="", tag=""):
        seen is None or seen.append((tag, prompt))
        return {"cleanup-reword": reword, "cleanup-check": check, "cleanup-merge": merge, "cleanup-pair": pair}[tag], 1
    return ask


class Rules(Base):
    def setUp(self):
        super().setUp()
        self.fresh = {l: situations.add(l, "seed", f"fresh {l}", date=TODAY) for l in "ab"}  # no rule fires on these

    def run_(self, **kw):
        with mock.patch.object(brain, "ask", model(**kw)):
            return cleanup.run_now(TODAY)

    def kinds(self, made):
        return [k for k, _ in made]

    def bump(self, lid, key, n):
        for _ in range(n):
            capstats.bump(lid, key)

    def test_a_quiet_store_queues_nothing(self):
        self.assertEqual(self.run_(), [])

    def test_often_wrong_is_a_reword(self):
        self.bump("a", "wrong", 3), self.bump("a", "right", 1)
        made = self.run_()
        self.assertEqual(self.kinds(made), ["edit"])
        self.assertIn("reword lesson a to: NEW WORDS", made[0][1])
        self.assertEqual(proposals.read()[0]["data"], {"lesson_id": "a", "text": "NEW WORDS"})

    def test_wrong_but_mostly_right_is_not(self):
        self.bump("a", "wrong", 3), self.bump("a", "right", 5)
        self.assertEqual(self.run_(), [])

    def test_often_missed_is_a_reword(self):
        self.bump("b", "missed", 3)
        self.assertEqual(self.kinds(self.run_()), ["edit"])

    def test_cases_matching_no_situation_are_a_reword_and_the_notes_are_used_up(self):
        cleanstate.note_new("a", "x"), cleanstate.note_new("a", "y")
        self.assertEqual(self.kinds(self.run_()), ["edit"])
        self.assertNotIn("a", cleanstate.read()["newkind"])

    def test_a_situation_without_a_hit_for_four_weeks_is_retired_a_recent_hit_keeps_it(self):
        old = situations.add("a", "seed", "old one", date=OLD)
        kept = situations.add("b", "seed", "old but hit", date=OLD)
        situations.hit(kept, "2026-11-10")
        made = self.run_()
        self.assertEqual((self.kinds(made), proposals.read()[0]["data"]), (["retire-situation"], {"sid": old}))

    def test_a_lesson_with_every_situation_retired_that_was_never_named_is_retired(self):
        situations.retire(self.fresh["b"])
        self.bump("a", "ignored", 1)
        situations.retire(self.fresh["a"])  # a was named once: it stays
        made = self.run_()
        self.assertEqual((self.kinds(made), proposals.read()[0]["data"]), (["retire-lesson"], {"lesson_id": "b"}))

    def test_a_merge_keeps_every_active_situation_linked(self):
        extra = situations.add("b", "correction", "second one of b", "d", "o", date=TODAY)
        retired = situations.add("b", "seed", "gone", date=TODAY, status="retired")
        with mock.patch.object(alllessons, "SIZE_LIMIT", 10):
            made = self.run_(merge="MERGE a,b | ONE WORDING")
        self.assertEqual(self.kinds(made), ["merge"])
        row = proposals.read()[0]
        self.assertEqual(row["data"], {"into": "a", "from": ["b"], "text": "ONE WORDING"})
        propapply.apply(row)
        active = {r["sid"]: r["lesson_id"] for r in situations.read() if r["status"] == "active"}
        self.assertEqual(active, {self.fresh["a"]: "a", self.fresh["b"]: "a", extra: "a"})
        self.assertEqual((self.lesson("a"), retired in active), ("ONE WORDING", False))

    def test_no_merge_while_under_the_size_limit(self):
        self.assertEqual(self.run_(merge="MERGE a,b | ONE WORDING"), [])

    def test_a_draft_that_fails_the_check_is_not_queued(self):
        self.bump("a", "missed", 3)
        self.assertEqual((self.run_(check="FAIL | drops the second case"), proposals.read()), ([], []))
        with mock.patch.object(alllessons, "SIZE_LIMIT", 10):
            self.assertEqual(self.run_(merge="MERGE a,b | W", check="FAIL | x"), [])

    def test_a_draft_with_a_private_path_is_not_queued(self):
        self.bump("a", "missed", 3)
        self.assertEqual(self.run_(reword=r"see C:\work\private\a.py"), [])

    def test_never_more_than_one_proposal_per_lesson(self):
        situations.add("a", "seed", "old one", date=OLD)
        self.bump("a", "missed", 3)
        self.assertEqual(self.kinds(self.run_()), ["edit"])  # the retire waits
        self.assertEqual(self.run_(), [])  # and nothing more while the reword is open

    def test_a_lesson_with_a_text_proposal_this_month_is_not_reworded_again(self):
        self.bump("a", "missed", 3)
        proposals.queue("edit", "reword lesson a to: X", {"lesson_id": "a", "text": "X"})
        proposals.change(lambda rs: rs[0].update(status="dropped", created="2026-11-10"))
        self.assertEqual(self.run_(), [])

    def test_counts_are_read_since_the_last_applied_edit(self):
        self.bump("a", "missed", 3)
        row = self.applied_edit("a")
        self.assertEqual(self.run_(), [])  # the 3 misses were before it
        self.assertEqual(row["data"]["stats_at"]["missed"], 3)

    def applied_edit(self, lid, text="W"):
        pid = proposals.queue("edit", f"reword {lid}", {"lesson_id": lid, "text": text})
        row = self.row(pid)
        propapply.apply(row)
        proposals.change(lambda rs: rs[0].update(status="applied", data=row["data"], created="2026-01-01"))
        return row

    def test_missed_rising_after_an_edit_queues_the_old_wording_back_once(self):
        row = self.applied_edit("a")
        self.assertEqual((row["data"]["old"], self.lesson("a")), ("L-a", "W"))
        self.bump("a", "missed", 1)
        self.assertEqual(self.run_(), [])
        self.bump("a", "missed", 1)
        made = self.run_()
        self.assertEqual(self.kinds(made), ["revert"])
        self.assertEqual(proposals.read()[-1]["data"], {"lesson_id": "a", "text": "L-a", "of": "p0001"})
        proposals.change(lambda rs: rs[-1].update(status="dropped"))
        self.assertEqual(self.run_(), [])  # asked once

    def test_the_weekly_run_is_due_once_a_week_and_daily_when_over_the_limit(self):
        self.assertTrue(cleanrun.due(TODAY))
        cleanstate.change(lambda s: s.update(last_run="2026-11-18"))
        self.assertFalse(cleanrun.due(TODAY))
        self.assertTrue(cleanrun.due("2026-11-25"))
        with mock.patch.object(alllessons, "SIZE_LIMIT", 10):
            self.assertTrue(cleanrun.due("2026-11-19"))


if __name__ == "__main__":
    unittest.main()
