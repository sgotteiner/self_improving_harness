// Parser edge cases (item 3 of the review): closing #, code fences, frontmatter, CRLF, second #, title fields.
const { t } = require("./test-helpers");
const { parse } = require("./sdd-lib");
const sec = (text) => parse(text).sections.map(s => s.title);
const msgs = (text) => parse(text).errors.map(e => e.msg);

t("parser: '## Learn C#' keeps its #", sec("# P\n\n## Learn C#\nid: a\nfeature: x\n").join("|") === "Learn C#");
t("parser: a space-preceded closing # run is stripped", sec("# P\n\n## Title ##\nid: a\nfeature: x\n").join("|") === "Title");
for (const [name, open, close] of [["```", "```", "```"], ["~~~", "~~~", "~~~"], ["longer ````", "````", "````"]]) {
  const p = parse(`# P\n\n## Real\nid: a\nfeature: x\n\n${open}\n## Fake\n${close}\n\n## After\nid: b\nfeature: y\n`);
  t(`parser: a heading inside a ${name} fence is not a section`, p.sections.map(s => s.title).join("|") === "Real|After" && p.errors.length === 0, JSON.stringify(p.errors));
}
let p = parse("# P\n\n## Real\nid: a\nfeature: x\n\n````\n```\n## Fake\n```\n````\n\n## After\nid: b\nfeature: y\n");
t("parser: a shorter fence inside a longer one does not close it", p.sections.map(s => s.title).join("|") === "Real|After");
p = parse("# P\n\n## Real\nid: a\nfeature: x\n\n```\n## Fake\n~~~\n## Fake2\n```\n\n## After\nid: b\nfeature: y\n");
t("parser: a ~~~ line does not close a ``` fence", p.sections.map(s => s.title).join("|") === "Real|After");
p = parse("---\n# a comment in the frontmatter\ntags: x\n---\n# Project\nfeature: A thing.\n\n## One\nid: one\nfeature: x\n");
t("parser: frontmatter with a # comment is skipped", p.title === "Project" && p.errors.length === 0 && p.sections.length === 1, JSON.stringify(p.errors));
p = parse("# P\n\n---\n\n## One\nid: one\nfeature: x\n");
t("parser: a --- later in the file is not frontmatter", p.sections.length === 1 && p.errors.length === 0);
p = parse("# P\r\nfeature: A thing.\r\n\r\n## One\r\nid: one\r\nfeature: x\r\ncontinued\r\n\r\ntext\r\n");
t("parser: CRLF line endings give clean titles and values", p.title === "P" && p.sections[0].title === "One" && p.sections[0].fields.id === "one" && p.root.fields.feature === "A thing.", JSON.stringify(p.sections[0].fields));
p = parse("# P\n\n## One\nid: one\nfeature: x\n\n# Second\n\n## Two\nid: two\nfeature: y\n");
t("parser: a second level-1 heading is an error", msgs("# P\n\n## One\nid: one\nfeature: x\n\n# Second\n").join("|").includes("second level-1 heading"), msgs("# P\n# Q\n").join("|"));
t("parser: the title may carry feature and open, not id/after/related", msgs("# P\nid: x\nafter: y\nrelated: z\nfeature: ok\nopen: ok\n").length === 3 && parse("# P\nfeature: ok\nopen: ok\n").errors.length === 0, msgs("# P\nid: x\n").join("|"));
t("parser: a skipped level is an error", msgs("# P\n\n## A\nid: a\nfeature: x\n\n#### C\nid: c\nfeature: x\n").join("|") === "heading jumps from level 2 to 4");
t("parser: a ### directly under the title is an error", /top-level feature must be a level-2/.test(msgs("# P\n\n### A\nid: a\nfeature: x\n").join("|")));
t("parser: unknown field", msgs("# P\n\n## A\nid: a\nfeature: x\ncolor: red\n").join("|") === 'unknown field "color:" (fields: id, feature, after, related, value, open, tag)');
t("parser: duplicate field", msgs("# P\n\n## A\nid: a\nfeature: x\nfeature: y\n").join("|") === 'field "feature:" given twice');
t("parser: an indented line continues a field", parse("# P\n\n## A\nid: a\nfeature: one\n  two\n").sections[0].fields.feature === "one two");
