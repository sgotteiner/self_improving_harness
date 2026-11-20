"""Shared by the proposal tests: a temp cases folder with two lessons (a, b), the queue and every store pointed at temp files."""
import datetime, os, tempfile, unittest
from unittest import mock

import helpers as h
import brain, capowed, capverdict, capwrite, casesave, ctx, history, index, proposals

LESSON = '---\nid: {i}\ndate: 2026-11-01\nsituation:\n  - "hand"\nright: "R-{i}"\nlesson: "L-{i}"\n---\n'
GOOD = {"situation": "reporting a fix", "did": "said fixed untested", "disliked": "(not stated)", "his_words": "test it first",
        "lesson": "show the output before saying done", "slug": "show-output"}
TP = "tp"
TODAY = str(datetime.date.today())  # the day propread.waiting marks as shown


def shown(text):
    """An assistant reply that ended with the proposal line, as the session was told to."""
    return f"Fixed it. Want me to run the other check too?\n\nproposal: {text} — yes / ignore"


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.cases = os.path.join(self.d, "cases")
        os.makedirs(self.cases)
        for i in ("a", "b"):
            open(os.path.join(self.cases, i + ".md"), "w", encoding="utf-8").write(LESSON.format(i=i))
        for p in (mock.patch.object(index, "CASES", self.cases), mock.patch.object(casesave, "PENDING", os.path.join(self.cases, "_pending")),
                  mock.patch.object(capwrite, "PENDING", os.path.join(self.cases, "_pending")), mock.patch.object(history, "spawn_sync"),
                  mock.patch.object(proposals, "path", lambda: os.path.join(self.cases, "_pending", "proposals.jsonl")),
                  mock.patch.object(proposals, "OFF_MARK", os.path.join(self.d, "off")),
                  mock.patch.object(proposals.ctx, "enabled", return_value=True),
                  mock.patch.object(history, "DB", os.path.join(self.d, "h.db")), mock.patch.object(capowed, "OWED", os.path.join(self.d, "o.json")),
                  mock.patch.object(capverdict, "AWAITING", os.path.join(self.d, "aw.json")),
                  mock.patch.object(ctx, "LOG", os.path.join(self.d, "hook.log"))):  # the tests never write the real hook.log
            p.start()
            self.addCleanup(p.stop)

    def lesson(self, cid="a"):
        return index.parse(os.path.join(self.cases, cid + ".md"))["lesson"]

    def row(self, pid="p0001"):
        return next(r for r in proposals.read() if r["pid"] == pid)

    def offer(self, kind, text, data, tp=TP, today=TODAY):
        """Queue a proposal and offer it to session tp; returns its pid."""
        pid = proposals.queue(kind, text, data)
        self.assertIn(text, proposals.line(tp, today))
        return pid

    def ask(self, model, reply="", tp=TP):
        """One message-step call in session tp after the assistant's `reply`; the model answers `model` (an Exception = a failed call)."""
        with mock.patch.object(brain, "ask", side_effect=model if isinstance(model, Exception) else None, return_value=(model, 1)) as m:
            out = capverdict.ask(tp, "PROMPT", "delegate-in", reply)[0]
        self.prompt = m.call_args[0][0]
        return out
