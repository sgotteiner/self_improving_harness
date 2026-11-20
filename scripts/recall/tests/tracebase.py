"""Shared setup of the feature-trace tests: a project folder, a temp traces folder, one session's transcript path."""
import os
from unittest import mock

import helpers as h
import brain, ctx, delegate, tracing
from propbase import Base


class TraceBase(Base):
    def setUp(self):
        super().setUp()
        self.proj = os.path.join(self.d, "myproj")
        os.makedirs(self.proj)
        self.tps = []
        open(os.path.join(self.proj, "CLAUDE.md"), "w").write("x")
        for p in (mock.patch.object(tracing, "DIR", os.path.join(self.d, "traces")), mock.patch.object(ctx, "enabled", return_value=True),
                  mock.patch.dict(os.environ, {"RECALL_WORK_STATE": os.path.join(self.d, "w.json")})):
            p.start()
            self.addCleanup(p.stop)

    def step(self, prompt, reply, entries=None):
        """One message step on `prompt` where the model answers `reply`; -> (instruction lines, the prompt the model got)."""
        tp = self.tp_for(entries or [h.user("earlier we saw the graph memory not work"), h.assistant("yes"), h.user(prompt)])
        ask = h.brain_says(reply)
        with mock.patch.object(brain, "ask", ask):
            return delegate.input_step(prompt, tp)[0], ask.prompts[0], tp

    def tp_for(self, entries):
        """The one session's transcript (the same path at every message, as in a real session), holding `entries`."""
        new = h.transcript(entries, cwd=self.proj)
        if not self.tps:
            self.tps.append(new)
            return new
        os.replace(new, self.tps[0])
        return self.tps[0]

    @property
    def tp1(self):
        return self.tps[0]

    def rows(self):
        return tracing.read("myproj")

    def open_one(self):
        self.step("add tracing of features", "TASK\nNONE\nTRACE NEW | Feature tracing | the graph memory did not work")
        return self.rows()[0]

    def other_session(self):
        return h.transcript([h.user("another window"), h.assistant("ok"), h.user("go")], cwd=self.proj)
