"""Feature traces: the message step's TRACE line opens a trace with its why, a follow-up attaches to it, events by code (his correction,
an agent return, a commit) are added to it, his done closes it and gives the session exactly one record instruction, and the work review
reads the closed trace. No test writes a real file: traces go to a temp folder, the brain is mocked."""
import os, tempfile, unittest
from unittest import mock

import helpers as h
import brain, delegate, tracechange, tracing, traceevents, workreview
from tracebase import TraceBase


class Traces(TraceBase):


    def test_a_task_opens_a_trace_with_its_why_and_the_title_is_not_read_as_a_flag(self):
        lines, prompt, _ = self.step("add tracing", "TASK\nNONE\nTRACE NEW | Trace the DONE flags | the graph memory did not work")
        (r,) = self.rows()
        self.assertEqual((r["tid"], r["title"], r["why"], r["closed"]), ("t1", "Trace the DONE flags", "the graph memory did not work", None))
        self.assertIn("(none)", prompt)  # no open traces yet
        self.assertEqual(len(lines), 2)  # TASK + TESTS; "DONE" in the title did not add the done line
        self.assertFalse(any("closed" in l for l in lines))

    def test_a_follow_up_attaches_to_the_open_trace_instead_of_a_new_one(self):
        self.open_one()
        _, prompt, _ = self.step("the stats are by my approval", "TALK\nNONE\nTRACE t1")
        self.assertIn("- t1: Feature tracing", prompt)
        (r,) = self.rows()
        self.assertEqual([e["type"] for e in r["events"]], ["message"])

    def test_a_correction_adds_one_event_to_the_open_trace_even_without_a_tid(self):
        self.open_one()
        tracechange.apply(self.tp1, "myproj", "", "CORRECTION", "no, that is wrong", False)
        (r,) = self.rows()
        self.assertEqual([(e["type"], e["text"]) for e in r["events"]], [("correction", "no, that is wrong")])

    def test_an_agent_return_and_a_commit_each_add_one_event_and_a_repeat_adds_none(self):
        self.open_one()
        a, b = h.tool("Agent", {"subagent_type": "reviewer", "description": "review", "prompt": "p"}), h.tool("Bash", {"command": "git commit -m x"})
        tp = self.tp_for([h.user("go"), h.assistant(a), h.result(a["id"], "Found 2 problems in the retry."), h.assistant(b),
                          h.result(b["id"], "[main 26f5cf2] Add the retry\n 2 files changed, 5 insertions(+)"), h.assistant("done")])
        for _ in range(2):
            traceevents.at_stop(tp)
        (r,) = self.rows()
        self.assertEqual([(e["type"], e["text"]) for e in r["events"]],
                         [("agent", "reviewer: Found 2 problems in the retry."), ("commit", "26f5cf2 Add the retry")])

    def test_event_text_from_tool_output_with_a_private_path_is_redacted(self):
        self.open_one()
        b = h.tool("Bash", {"command": "git commit -m x"})
        tp = self.tp_for([h.user("go"), h.assistant(b), h.result(b["id"], r"[main abcdef1] fix C:\work\private\x.py" + "\n 1 file changed")])
        traceevents.at_stop(tp)
        self.assertEqual(self.rows()[0]["events"][0]["text"], "abcdef1 (redacted)")

    def test_events_with_no_open_trace_write_nothing(self):
        b = h.tool("Bash", {"command": "git commit -m x"})
        traceevents.at_stop(h.transcript([h.user("go"), h.assistant(b), h.result(b["id"], "[main abcdef1] x\n 1 file changed")], cwd=self.proj))
        self.assertFalse(os.path.exists(tracing.DIR))

    def test_done_closes_the_trace_and_the_session_is_told_once_to_record_it(self):
        self.open_one()
        lines, _, _ = self.step("it works, done", "TALK\nDONE\nTRACE t1")
        rec = [l for l in lines if "Feature trace closed" in l and "Feature trace t1" in l]
        self.assertEqual(len(rec), 1)
        self.assertIn("Why: the graph memory did not work", rec[0])
        self.assertTrue(self.rows()[0]["closed"])
        lines, _, _ = self.step("thanks, done", "TALK\nDONE\nTRACE NONE")  # nothing open any more
        self.assertFalse(any("Feature trace" in l for l in lines))

    def test_the_work_review_gets_the_closed_trace_with_its_events_once(self):
        self.open_one()
        tracechange.apply(self.tp1, "myproj", "t1", "CORRECTION", "wrong table", False)
        self.step("done", "TALK\nDONE\nTRACE t1")
        tp = self.tp_for([h.user("add tracing"), h.assistant("ok"), h.user("done")])  # the session that opened and closed the trace
        asked = []
        with mock.patch.object(brain, "ask", side_effect=lambda p, system="", tag="": (asked.append(p), ("NONE", 1))[1]):
            workreview.run(tp)
            workreview.run(tp)
        self.assertIn("Feature trace t1: Feature tracing", asked[0])
        self.assertIn("correction: wrong table", asked[0])
        self.assertTrue(all("Feature trace" not in p for p in asked[1:]))  # read once

    def test_no_project_means_no_trace_and_the_message_step_still_answers(self):
        tp = h.transcript([h.user("x"), h.assistant("y"), h.user("add it")], cwd=tempfile.mkdtemp())
        with mock.patch.object(brain, "ask", h.brain_says("TASK\nNONE\nTRACE NEW | T | w")):
            self.assertEqual(len(delegate.input_step("add it", tp)[0]), 2)
        self.assertFalse(os.path.exists(tracing.DIR))
        self.assertEqual(tracing.project(h.transcript([h.user("x")])), "")  # no cwd recorded: not the hook's own folder


if __name__ == "__main__":
    unittest.main()
