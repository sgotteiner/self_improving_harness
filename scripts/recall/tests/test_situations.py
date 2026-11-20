"""The situations store: seeded once from the hand-written lines and the cleaned history.db rows, each row added exactly once (by its
row id), no lost lines under concurrent writers, history pages and LESSONS.md generated from it, the gate's all-lessons text unchanged."""
import json, os, tempfile, threading, unittest
from unittest import mock

import helpers as h
import alllessons, embed, history, index, mdfile, situations, views

LESSON = '---\nid: {i}\ndate: 2026-11-01\nsituation:\n  - "hand one"\n  - hand two\nright: "R-{i}"\nlesson: "L-{i}"\n---\n'
PAGE = ("# a: real occurrences, cleaned\n\nHEAD\n\n## 2026-11-02 | correction\n- situation: s1\n- assistant did: d1\n"
        "- he did not like: o1\n- lesson: L-a\n\n## 2026-11-03 | gate\n- situation: s2\n- assistant did: d2\n"
        "- he did not like: o2\n- lesson: L-a\n")


def blocks(text):
    return text[text.index("## "):]


def clean_json(n):
    return json.dumps({"situation": f"s{n}", "assistant_did": f"d{n}", "disliked": f"o{n}"})


class Store(unittest.TestCase):
    def setUp(self):
        self.cases = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.cases, "history"))
        for i in ("a", "b"):
            open(os.path.join(self.cases, i + ".md"), "w", encoding="utf-8").write(LESSON.format(i=i))
        for p in (mock.patch.object(index, "CASES", self.cases), mock.patch.object(history, "DB", os.path.join(self.cases, "h.db")),
                  mock.patch.object(history, "spawn_sync")):
            p.start()
            self.addCleanup(p.stop)
        history.add("a", "correction", "raw", date="2026-11-02", clean_text=clean_json(1))  # row 1
        history.add("a", "gate", "raw", date="2026-11-03", clean_text=clean_json(2))  # row 2
        history.add("pending-one", "gate", "raw", clean_text=clean_json(3))  # a lesson not approved
        history.add("a", "gate", "raw")  # not cleaned yet

    def page(self, cid="a"):
        return open(os.path.join(self.cases, "history", cid + ".md"), encoding="utf-8").read()

    def sync(self):
        with mock.patch.dict("sys.modules", {"clean": mock.Mock(clean=lambda *a: None)}), mock.patch.object(embed, "encode"):
            history.sync()

    def test_seed_and_sync_give_each_line_exactly_one_line_and_are_repeatable(self):
        self.assertEqual(situations.seed(), 4)  # 2 hand lines each of a and b
        self.sync()
        self.sync()
        rows = situations.read()  # the row of a lesson not yet approved waits
        self.assertEqual(len({r["sid"] for r in rows}), 6)
        self.assertEqual(sorted(r["source"] for r in rows if r["lesson_id"] == "a"), ["correction", "gate", "seed", "seed"])
        self.assertTrue(all(r["status"] == "active" and r["hits"] == 0 and r["last_hit"] is None for r in rows))
        self.assertEqual(situations.seed(), 0)

    def test_a_line_from_before_row_ids_counts_as_there_and_a_cleaned_row_is_added_once(self):
        situations.add("a", "correction", "s1", "d1", "o1", "2026-11-02")
        self.sync()
        self.assertEqual(sorted(r["situation"] for r in situations.read()), ["s1", "s2"])
        self.assertEqual([r["occ"] for r in situations.read()], [None, 2])

    def test_a_line_with_a_known_row_id_is_refused_and_two_writers_never_share_a_sid(self):
        self.assertEqual(situations.add("a", "gate", "x", occ=7), "s0001")
        self.assertIsNone(situations.add("a", "gate", "x", occ=7))
        ts = [threading.Thread(target=lambda i=i: situations.add("a", "gate", f"w{i}", occ=100 + i)) for i in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        sids = [r["sid"] for r in situations.read()]
        self.assertEqual((len(sids), len(set(sids))), (9, 9))
        with mdfile.held(situations.path() + ".lock"), mock.patch.object(mdfile, "LOCK_TRIES", 2), mock.patch.object(mdfile, "LOCK_WAIT", 0):
            with self.assertRaises(OSError):
                situations.add("a", "gate", "y")

    def test_regenerated_pages_hold_the_same_blocks_and_seed_lines_stay_off_them(self):
        situations.seed()
        self.sync()
        self.assertEqual(views.build(), ["a"])
        self.assertEqual(blocks(self.page()), blocks(PAGE))
        self.assertFalse(os.path.exists(os.path.join(self.cases, "history", "b.md")))
        before = self.page()
        views.build()
        self.assertEqual(self.page(), before)
        self.assertEqual(index.history_texts("a"), ["Situation: s1 Assistant did: d1 He did not like: o1",
                                                    "Situation: s2 Assistant did: d2 He did not like: o2"])

    def test_the_all_lessons_text_is_what_the_lesson_files_say(self):
        want = "\n".join(f"- {i}: Lesson: L-{i} Right: R-{i}" for i in ("a", "b"))
        self.assertEqual(alllessons.block(alllessons.lessons()), want)
        views.build()  # LESSONS.md next to the lessons is not a lesson
        self.assertEqual(alllessons.block(alllessons.lessons()), want)

    def test_lessons_md_lists_every_lesson_with_its_active_situations_only(self):
        situations.seed()
        sid = situations.add("b", "work", "work one", "d", "o")
        situations.retire(sid)
        situations.add("b", "work", "wait one", "d", "o", status=situations.PROPOSED)
        views.build()
        md = open(os.path.join(self.cases, "LESSONS.md"), encoding="utf-8").read()
        self.assertTrue(all(f"## {i}" in md and f"L-{i}" in md and f"R-{i}" in md for i in ("a", "b")))
        self.assertIn("hand one", md)
        self.assertNotIn("work one", md)
        self.assertNotIn("wait one", md)  # proposed: not shown until his yes

    def test_a_capture_write_adds_exactly_one_line_and_hit_retire_and_relink_touch_only_their_fields(self):
        situations.seed()
        history.record(os.path.join(self.cases, "a.md"), "correction", "raw words", clean_text=json.dumps(
            {"situation": "S", "assistant_did": "D", "disliked": "O"}))
        self.sync()  # the row is in the store already: sync does not add it again
        rows = [r for r in situations.read() if r["situation"] == "S"]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["lesson_id"], rows[0]["outcome"]), ("a", "O"))
        self.assertNotIn("raw words", open(situations.path(), encoding="utf-8").read())
        old = situations.read()
        situations.hit(old[0]["sid"], "2026-11-21")
        situations.retire(old[1]["sid"])
        self.assertEqual(situations.relink(["b"], "a"), 2)
        new = situations.read()
        self.assertEqual((new[0]["hits"], new[0]["last_hit"], new[1]["status"]), (1, "2026-11-21", "retired"))
        self.assertEqual({r["lesson_id"] for r in new}, {"a"})
        strip = lambda rs: [{k: v for k, v in r.items() if k not in situations.EDITABLE} for r in rs]
        self.assertEqual(strip(new), strip(old))
        with self.assertRaises(ValueError):
            situations.add("a", "invented", "x")


if __name__ == "__main__":
    unittest.main()
