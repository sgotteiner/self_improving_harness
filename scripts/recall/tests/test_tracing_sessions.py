"""Feature traces belong to the session that opened them: another session's done, correction, events or review never touch them; stale traces
are abandoned; the store is git-ignored."""
import datetime, json, os, subprocess, unittest

import tracechange, tracing
from tracebase import TraceBase


class Sessions(TraceBase):
    def test_a_done_in_another_session_never_closes_this_sessions_trace(self):
        self.open_one()
        tpb = self.other_session()
        for tline in ("t1", "", "NONE"):
            self.assertEqual(tracechange.apply(tpb, "myproj", tline, "TALK", "done", True), [])
        self.assertIsNone(self.rows()[0]["closed"])
        self.assertEqual(self.rows()[0]["events"], [])
        tracechange.apply(tpb, "myproj", "", "CORRECTION", "wrong", False)  # nor does his correction there attach
        self.assertEqual(self.rows()[0]["events"], [])

    def test_done_without_a_tid_closes_only_when_this_session_has_exactly_one_open_trace_and_none_never_attaches(self):
        self.open_one()
        self.assertEqual(tracechange.apply(self.tp1, "myproj", "NONE", "TALK", "done", True), [])
        self.assertIsNone(self.rows()[0]["closed"])
        tracechange.apply(self.tp1, "myproj", "NEW | Second | why", "TASK", "again", False)
        self.assertEqual(tracechange.apply(self.tp1, "myproj", "", "TALK", "done", True), [])  # two open: ambiguous
        self.assertEqual([r["closed"] for r in self.rows()], [None, None])
        self.assertEqual(len(tracechange.apply(self.tp1, "myproj", "t2", "TALK", "done", True)), 1)  # an explicit tid closes it
        self.assertEqual(len(tracechange.apply(self.tp1, "myproj", "", "TALK", "done", True)), 1)  # the single one left

    def test_the_review_takes_only_its_own_sessions_closed_trace(self):
        self.open_one()
        self.step("done", "TALK\nDONE\nTRACE t1")
        tpb = self.other_session()
        self.assertEqual(tracechange.take_closed(tpb), "")
        self.assertIn("Feature trace t1", tracechange.take_closed(self.tp1))
        self.assertEqual(tracechange.take_closed(self.tp1), "")

    def test_events_go_only_to_this_sessions_trace(self):
        self.open_one()
        tracechange.add_events(self.other_session(), "myproj", [("k", "commit", "x")])
        self.assertEqual(self.rows()[0]["events"], [])

    def test_a_trace_with_no_event_for_the_stale_days_is_abandoned_not_deleted_and_not_listed(self):
        self.open_one()
        rows = self.rows()
        rows[0]["opened"] = (datetime.datetime.now() - datetime.timedelta(days=tracing.STALE_DAYS + 1)).isoformat(timespec="seconds")
        open(tracing.path("myproj"), "w").write(json.dumps(rows[0]) + "\n")
        self.assertNotIn("t1:", tracing.ask_text(self.tp1, "myproj"))
        self.assertEqual(tracechange.apply(self.tp1, "myproj", "t1", "TALK", "done", True), [])
        (r,) = self.rows()
        self.assertTrue(r["abandoned"])
        self.assertIsNone(r["closed"])

    def test_the_prompt_lists_at_most_the_open_list_max_open_traces(self):
        self.open_one()
        for i in range(tracing.OPEN_LIST_MAX + 2):
            tracechange.apply(self.tp1, "myproj", f"NEW | Feature {i} | w", "TASK", "x", False)
        self.assertEqual(tracing.ask_text(self.tp1, "myproj").count("\n- t"), tracing.OPEN_LIST_MAX)

    def test_events_do_not_crash_when_the_open_trace_vanished_between_the_check_and_the_write(self):
        self.open_one()
        tracechange.apply(self.tp1, "myproj", "t1", "TALK", "done", True)
        tracechange.add_events(self.tp1, "myproj", [("k", "commit", "x")])  # no open trace left
        self.assertEqual([e["type"] for e in self.rows()[0]["events"]], ["done"])

    def test_traces_are_git_ignored(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.assertEqual(subprocess.run(["git", "check-ignore", "-q", "traces/x.jsonl"], cwd=root).returncode, 0)


if __name__ == "__main__":
    unittest.main()
