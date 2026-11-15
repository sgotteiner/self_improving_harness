"""Diary side of decision capture: approve (placement, CRLF, atomic, twice), discard, diary_for in three layouts."""
import json, os, tempfile, unittest
from unittest import mock

import helpers as h
import brain, ctx, decisions, diary, mdfile, pending

SECTION = diary.SECTION
DIARY = f"# Diary\n\n## Feature: maps\n\n### Old\n**Idea:** x\n**Why:** y\n\n---\n\n{SECTION}\n\n### First\n**Idea:** a\n**Why:** b\n\n---\n\n## Feature: later\n\ntext\n"
DRAFT = ('---\nid: new-one\ndate: 2026-11-15\nproject: "p"\ntarget: "{t}"\nsession: abcd1234\nstatus: pending\nasked: false\n'
         'title: "New one"\nkind: decision\nportable: no\nimportance: normal\nidea: "the idea"\nwhy: "(not stated)"\nhis_words: "w"\n---\n')


class Env(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.diary = os.path.join(self.d, "diary.md")
        diary.PENDING, pending.TODO = os.path.join(self.d, "pend"), os.path.join(self.d, "todo.md")
        os.makedirs(diary.PENDING)
        open(pending.TODO, "w").write("- [ ] diary entry suggested `new-one` (diary-pending/new-one.md): add or discard\nDone\n")

    def draft(self, slug="new-one"):
        open(os.path.join(diary.PENDING, slug + ".md"), "w", encoding="utf-8").write(DRAFT.format(t=self.diary.replace("\\", "/")))


class Approve(Env):
    def test_entry_goes_under_its_section_not_at_the_end(self):
        open(self.diary, "w", encoding="utf-8", newline="").write(DIARY)
        self.draft()
        self.assertEqual(diary.approve("new-one"), 0)
        t = open(self.diary, encoding="utf-8").read()
        self.assertTrue(t.index("### First") < t.index("### New one") < t.index("## Feature: later"), t)
        self.assertTrue(t.index("### New one") < t.index("---", t.index("### New one")))  # before the rule that closes the section
        self.assertEqual(t.replace("### New one", "").count("**Why:** y"), 1)
        self.assertIn(DIARY.split(SECTION)[0], t)  # what was there is untouched
        self.assertFalse(os.path.exists(os.path.join(diary.PENDING, "new-one.md")))
        self.assertNotIn("new-one", open(pending.TODO).read())

    def test_last_section_and_missing_section(self):
        for text in (DIARY.split("---\n\n## Feature: later")[0].rstrip() + "\n", "# Diary\n\n### Old\n**Idea:** x\n"):
            open(self.diary, "w", encoding="utf-8", newline="").write(text)
            self.draft()
            diary.approve("new-one")
            t = open(self.diary, encoding="utf-8").read()
            self.assertTrue(t.startswith(text.rstrip()) and t.rstrip().endswith("**Why:** (not stated)") and t.count(SECTION) == 1, t)

    def test_crlf_is_kept(self):
        open(self.diary, "w", encoding="utf-8", newline="").write(DIARY.replace("\n", "\r\n"))
        self.draft()
        diary.approve("new-one")
        raw = open(self.diary, "rb").read()
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"), "every line ending must stay CRLF")
        self.assertIn(b"### New one\r\n", raw)

    def test_atomic_a_failed_write_leaves_the_diary_and_draft(self):
        open(self.diary, "w", encoding="utf-8", newline="").write(DIARY)
        self.draft()
        with mock.patch("os.replace", side_effect=OSError("locked")):
            with self.assertRaises(OSError):
                diary.approve("new-one")
        self.assertEqual(open(self.diary, encoding="utf-8").read(), DIARY)
        self.assertTrue(os.path.exists(os.path.join(diary.PENDING, "new-one.md")))
        self.assertEqual([f for f in os.listdir(self.d) if f.endswith(".tmp")], [], "no temp file left behind")

    def test_twice_and_after_a_crash_appends_once(self):
        open(self.diary, "w", encoding="utf-8", newline="").write(DIARY)
        self.draft()
        diary.approve("new-one")
        self.assertEqual(diary.approve("new-one"), 0)  # draft gone: "no pending draft", exit 0
        self.draft()  # a crash between the write and the delete left the draft behind
        self.assertEqual(diary.approve("new-one"), 0)
        self.assertEqual(open(self.diary, encoding="utf-8").read().count("### New one"), 1)

    def test_discard_and_bad_slugs(self):
        self.draft()
        self.assertEqual(diary.discard("new-one"), 0)
        self.assertEqual(diary.discard("new-one"), 0)  # again: not an error
        self.assertFalse(os.path.exists(os.path.join(diary.PENDING, "new-one.md")))
        for bad in ("../x", "a/b", "a\\b", ""):
            self.assertEqual(diary.approve(bad), 2)
            self.assertEqual(diary.discard(bad), 2)


class DiaryFor(Env):
    def project(self, claude, files=()):
        p = tempfile.mkdtemp()
        os.makedirs(os.path.join(p, "docs"))
        for f in files:
            open(os.path.join(p, f), "w").write("# d")
        if claude:
            open(os.path.join(p, "CLAUDE.md"), "w").write(claude)
        return p

    def test_three_layouts(self):
        open(self.diary, "w").write("# d")
        with mock.patch.object(diary, "DIARY_SETUP", self.diary):
            self.assertEqual(diary.diary_for(ctx.ROOT), self.diary)  # 1: the setup keeps it in the vault
        p = self.project("# P\n## Project documents\n- **SDD:** `docs/s.md`\n- **Diary:** `docs/DESIGN_DECISIONS_DIARY.md` (+ `docs/DIARY_FLAGS.md`)\n",
                         ["docs/DESIGN_DECISIONS_DIARY.md", "docs/DIARY_FLAGS.md"])
        self.assertEqual(diary.diary_for(p), os.path.join(p, "docs", "DESIGN_DECISIONS_DIARY.md"))  # 2: named in the project's CLAUDE.md
        self.assertEqual(diary.flags_for(p), os.path.join(p, "docs", "DIARY_FLAGS.md"))
        q = self.project("# P\n## Project documents\n- **SDD:** `docs/s.md`\n", ["docs/design_diary.md"])
        self.assertEqual(diary.diary_for(q), "")  # 3: not named: not guessed from a *diary*.md, he is asked
        self.assertEqual(diary.diary_for(self.project("", ["docs/design_diary.md"])), "")

    def test_the_last_cwd_of_the_transcript(self):
        tp = h.transcript([h.user("a")], cwd="C:/first")
        open(tp, "a").write(json.dumps({"type": "user", "cwd": "C:/second", "message": {"content": "b"}}) + "\n")
        self.assertEqual(diary.project_of(tp), "C:/second")


if __name__ == "__main__":
    unittest.main()
