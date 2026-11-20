"""Cleanup of the lessons: queues proposals (proposals.py shows one a day, his yes applies it) from the rules in cleanrules.py:
reword (often wrong, often missed, new kinds keep coming), retire a situation or a lesson, merge same-kind lessons when the
all-lessons text is over alllessons.SIZE_LIMIT, revert an edit or merge after which `missed` rose. A reworded or merged text is
checked (cleandraft.why_not) against its lessons and their active situations before it is queued (a failing one is logged, not
queued). Never more than one open proposal per lesson. cleanrun.py decides when a run happens and runs it."""
import datetime, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alllessons, capstats, cleandraft, cleanrules as R, cleanstate, ctx, proposals, situations, views


def over(ls):
    return len(alllessons.text(ls)) > alllessons.SIZE_LIMIT


class Run:
    def __init__(self, today):
        self.today, self.made = today, []
        self.ls, self.sits, self.stats = views.lessons(), situations.read(), capstats.get()
        self.rows, self.state = proposals.read(), cleanstate.read()
        self.notes = self.state.get("newkind", {})
        self.busy = R.busy(self.rows, self.sits)

    def active(self, *ids):
        return [s for s in self.sits if s["lesson_id"] in ids and s["status"] == "active"]

    def queue(self, kind, text, data, ids):
        self.busy |= R.busy(proposals.read(), self.sits)  # one open proposal per lesson, whatever its text
        if set(ids) & self.busy:
            return False
        if proposals.queue(kind, text, data):
            self.busy |= set(ids)
            self.made.append((kind, " ".join(text.split())))
            return True
        return False

    def reverts(self):
        for r, lid in R.reverts(self.rows, self.stats, self.today):
            old, back = r["data"]["old"], r["data"].get("from", [])  # back: the lessons a merge archived
            data = {"lesson_id": lid, "text": old, "of": r["pid"]}
            back and data.update(restore=back, moved=r["data"].get("moved", {}))
            self.queue("revert", f"revert lesson {lid} to: {old}" + (f", and restore {', '.join(back)}" if back else ""), data, [lid, *back])

    def rewords(self):
        for lid, why in R.reasons(self.ls, self.stats, self.rows, self.notes).items():
            if lid in self.busy or R.recent(self.rows, lid, self.today):
                continue
            _, lesson, right = self.ls[lid]
            sits = self.active(lid)
            text = cleandraft.reword(lesson, right, why, sits, self.notes.get(lid, []))
            bad = cleandraft.why_not(text, [(lid, lesson, right)], sits)
            if bad:
                ctx.log(f"cleanup: reword of {lid} not queued ({bad[:150]}): {text[:100]!r}")
            elif self.queue("edit", f"reword lesson {lid} to: {text} ({why})", {"lesson_id": lid, "text": text}, [lid]):
                cleanstate.change(lambda s: s.get("newkind", {}).pop(lid, None))

    def retires(self):
        for s in (s for s in R.stale(self.sits, self.today) if s["lesson_id"] in self.ls):
            self.queue("retire-situation", f"retire the situation of lesson {s['lesson_id']} no one hit for {R.RETIRE_WEEKS} weeks: "
                       f"{s['situation'][:100]}", {"sid": s["sid"]}, [s["lesson_id"]])
        for lid in R.dead(self.ls, self.sits, self.stats):
            self.queue("retire-lesson", f"retire lesson {lid}: all its situations are retired and the gate never named it", {"lesson_id": lid}, [lid])

    def merges(self):
        """Over the size limit: group same-kind lessons (one call, not repeated while the lessons are the same as when it last
        found none), then check each wording against its lessons and their situations."""
        fp = R.lesson_set(self.ls)
        if not over(self.ls) or self.state.get("merge_none") == fp:
            return
        found = cleandraft.merges(self.ls)
        if not found:
            cleanstate.change(lambda s: s.update(merge_none=fp))
        for ids, text in found:
            if set(ids) & self.busy or any(R.recent(self.rows, i, self.today) for i in ids):
                continue
            bad = cleandraft.why_not(text, [(i, *self.ls[i][1:]) for i in ids], self.active(*ids))
            if bad:
                ctx.log(f"cleanup: merge of {ids} not queued ({bad[:150]}): {text[:100]!r}")
            else:
                self.queue("merge", f"merge lessons {', '.join(ids)} into {ids[0]}: {text}", {"into": ids[0], "from": ids[1:], "text": text}, ids)


def go(today):
    """Queue what the rules find: ([(kind, text)] queued, [names of the steps that failed]). One failing step never stops the others."""
    r, failed = Run(today or str(datetime.date.today())), []
    for step in (r.reverts, r.rewords, r.retires, r.merges):
        try:
            step()
        except Exception as e:
            ctx.log(f"cleanup: {step.__name__} failed: {e!r}")
            failed.append(step.__name__)
    return r.made, failed


def run_now(today=None):
    return go(today)[0]
