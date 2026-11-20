"""Situation tracing: a firing on a known situation raises that situation's hits by one, an unlike case is flagged new kind, a
failed call changes nothing; his RIGHT verdict and a missed correction are the two ways a lesson fires, WRONG and NONE are not."""
import os, unittest
from unittest import mock

import brain, capstats, capverdict, capwrite, cleanstate, situations, situtrace
from propbase import Base, GOOD, TODAY


class Trace(Base):
    def setUp(self):
        super().setUp()
        self.s1 = situations.add("a", "seed", "pushed before the tests ran")
        self.s2 = situations.add("a", "correction", "said done after a failing run", "said done", "o")

    def hits(self):
        return {r["sid"]: r["hits"] for r in situations.read()}

    def test_a_firing_on_a_known_situation_raises_that_situations_hits_by_one(self):
        with mock.patch.object(brain, "ask", return_value=(f"`{self.s2}`", 1)):
            self.assertEqual(situtrace.fire("a", "claimed fixed with a red build"), self.s2)
        self.assertEqual(self.hits(), {self.s1: 0, self.s2: 1})
        self.assertEqual(next(r for r in situations.read() if r["sid"] == self.s2)["last_hit"], TODAY)

    def test_an_unlike_case_is_flagged_new_kind_and_noted_for_the_reword_rule(self):
        with mock.patch.object(brain, "ask", return_value=("NEW", 1)):
            self.assertEqual(situtrace.fire("a", "something else entirely"), "NEW")
        self.assertEqual((self.hits(), cleanstate.read()["newkind"]["a"]), ({self.s1: 0, self.s2: 0}, ["something else entirely"]))

    def test_only_that_lessons_active_situations_are_shown_and_none_means_no_call(self):
        situations.retire(self.s1)
        with mock.patch.object(brain, "ask", return_value=(self.s2, 1)) as m:
            situtrace.fire("a", "case")
            situtrace.fire("b", "case")  # no situation of b
        self.assertEqual(m.call_count, 1)
        self.assertIn(self.s2, m.call_args[0][0])
        self.assertNotIn("pushed before", m.call_args[0][0])

    def test_a_failed_or_unreadable_call_changes_nothing(self):
        for model in (RuntimeError("down"), ("maybe s0001?", 1)):
            with mock.patch.object(brain, "ask", **({"side_effect": model} if isinstance(model, Exception) else {"return_value": model})):
                self.assertIsNone(situtrace.fire("a", "case"))
        self.assertEqual((self.hits(), cleanstate.read()), ({self.s1: 0, self.s2: 0}, {}))

    def test_his_right_verdict_traces_wrong_and_none_do_not(self):
        capverdict.add("tp", "a", "claims it works with no run")
        with mock.patch.object(brain, "ask", return_value=(self.s1, 1)) as m:
            capverdict.settle("tp", capverdict.awaiting("tp"), "VERDICT a WRONG")
            capverdict.add("tp", "a", "again")
            capverdict.settle("tp", capverdict.awaiting("tp"), "")
            self.assertEqual((m.call_count, self.hits()[self.s1]), (0, 0))
            capverdict.add("tp", "a", "claims it works with no run")
            capverdict.settle("tp", capverdict.awaiting("tp"), "VERDICT a RIGHT")
        self.assertEqual((m.call_count, self.hits()[self.s1], capstats.get("a")["right"]), (1, 1, 1))

    def test_a_missed_correction_traces_and_leaves_its_own_new_situation_out(self):
        d = dict(GOOD, lesson_id="a", source="correction")
        del d["lesson"], d["slug"]
        with mock.patch.object(brain, "ask", return_value=(self.s1, 1)) as m:
            self.assertTrue(capwrite.write(d)[0])
        self.assertEqual(self.hits()[self.s1], 1)
        self.assertNotIn(GOOD["did"], m.call_args[0][0].split("A new case")[0])  # the stored copy of this case is not a candidate
        self.assertEqual(len(situations.read()), 3)  # the new situation stays linked to the lesson


if __name__ == "__main__":
    unittest.main()
