// Validator tests: the fixtures (exact output), each rule, the plain-words check, reserved ids, --since, a path with spaces.
const { fs, path, fx, validateCli, tmp, good, write, t, repo } = require("./test-helpers");
const { validate, plainWordsProblems } = require("./sdd-lib");
const msgs = (text, opt) => validate(text, opt).out.map(e => e.msg);
const one = (id, extra = "", feature = "Something plain.") => `## S ${id}\nid: ${id}\nfeature: ${feature}\n${extra}\n`;
const doc = (...secs) => "# P\n\n" + secs.join("\n");

let r = validateCli(path.join(fx, "good.md"));
t("validator: good fixture passes", r.code === 0 && r.out.trim() === "sdd ok; 8 sections", r.out.trim());
const D = "(plain words at the top; names, numbers and paths go from the second level down)";
const broken = {
  "broken-no-feature.md": 'broken-no-feature.md:12: section "Check the stock": lists criteria/files but has no feature or what/how above them (details need a feature above)\n1 problem',
  "broken-duplicate-id.md": 'broken-duplicate-id.md:43: section "Print the label": duplicate id "check-stock" (also on "Check the stock", line 12)\nbroken-duplicate-id.md:50: section "Hand over to the carrier": after names "print-label", which is not an id in this file\n2 problems',
  "broken-dangling.md": 'broken-dangling.md:39: section "Pack and send": related names "ghost-feature", which is not an id in this file\nbroken-dangling.md:50: section "Hand over to the carrier": after names "label-step", which is not an id in this file\n2 problems',
  "broken-top-level-detail.md": `broken-top-level-detail.md:38: section "Pack and send": top-level feature text has digits, a path or file name ${D}\n1 problem`,
};
for (const [f, want] of Object.entries(broken)) {
  r = validateCli(path.join(fx, f));
  t(`validator: ${f} fails with exactly the right output`, r.code === 1 && r.out.trim() === want, r.out.trim());
}
r = validateCli(write("noid.md", good.replace("id: stock\n", "")));
t("validator: a section without id fails", r.code === 1 && r.out.split("\n").includes('noid.md:53: section "Stock": has no id (every section needs `id: <stable-kebab-id>` right under its heading)'), r.out);

// ---- rules, in memory
t("validator: id not kebab-case", msgs(doc(one("Bad_Id"))).join() === 'id "Bad_Id" is not kebab-case (lowercase words joined by -)');
t("validator: reserved ids root and constructor", msgs(doc(one("root"), one("constructor"))).join("|") === 'id "root" is reserved (the map page uses it itself)|id "constructor" is reserved (the map page uses it itself)');
t("validator: duplicate id", /^duplicate id "a" \(also on "S a", line 3\)$/.test(msgs(doc(one("a"), one("a"))).join("|")));
t("validator: an after chain that loops", msgs(doc(one("a", "").replace("feature:", "after: b\nfeature:"), one("b").replace("feature:", "after: a\nfeature:"))).filter(m => /loops/.test(m)).length === 2);
t("validator: after its own id loops", msgs(doc(one("a").replace("feature:", "after: a\nfeature:"))).join() === 'after chain loops back through "a"');
t("validator: related to its own id", msgs(doc(one("a").replace("feature:", "related: a\nfeature:"))).join() === 'related names its own id "a"');
t("validator: unknown field and duplicate field reach the validator", msgs(doc(one("a").replace("feature:", "color: red\nfeature:"))).join() === 'unknown field "color:" (fields: id, feature, after, related, value, open, tag)');
t("validator: a skipped heading level", msgs(doc(one("a"), "#### Deep\nid: d\nfeature: x\n")).join() === "heading jumps from level 2 to 4");
t("validator: tag is accepted", msgs(doc(one("a").replace("feature:", "tag: Label\nfeature:"))).length === 0);
t("validator: no feature", msgs(doc("## A\nid: a\n")).join() === "has no feature (say in plain words what it is / what happens here)");
t("validator: a second # heading is reported", msgs(doc(one("a"), "# Another\n")).join() .startsWith("second level-1 heading"));
t("validator: id/after on the title are reported", msgs("# P\nid: x\n\n" + one("a")).join() === 'the title (#) may carry only feature and open, not "id:"');

// ---- plain words: what is flagged and what is not
const pw = (s) => plainWordsProblems(s).join("+");
for (const ok of ["Answer yes/no questions.", "Use and/or logic.", "The iPhone and eBay apps work with macOS.", "Learn C# and C++.", "Pays by card, or by transfer."])
  t(`plain words: not flagged: ${ok}`, pw(ok) === "", pw(ok));
const flagged = [["Reads shop/stock.py daily", "a path or file name"], ["Opens C:\\data\\x", "a path or file name"], ["Edits notes.md", "a path or file name"], ["Calls reserve_stock", "a code name"], ["Runs `now`", "a code name"],
  ["Calls getUser first", "a code name"], ["Calls run() now", "a code name"], ["Calls shop.pay(x) now", "a code name"], ["Waits 2 days", "digits"]];
for (const [s, want] of flagged) t(`plain words: flagged (${want}): ${s}`, pw(s) === want, pw(s));
r = validate(doc(one("a", "", "Answer yes/no with iPhone and/or eBay.")));
t("plain words: false positives pass the validator", r.out.length === 0, JSON.stringify(r.out));
t("plain words: only ## features are checked, not ### ones", msgs(doc(one("a"), "### Sub\nid: b\nfeature: Reads shop/stock.py in 2 days.\n")).length === 0);

// ---- --since, --removed, a path with spaces, a renamed SDD file
const { dir, g } = repo("repo with spaces");
fs.writeFileSync(path.join(dir, "my sdd.md"), good);
g("add", "."); g("commit", "-q", "-m", "first");
const c1 = g("rev-parse", "HEAD");
const renamed = good.replace("id: print-label", "id: label-printing").replace("after: print-label", "after: label-printing");
fs.writeFileSync(path.join(dir, "my sdd.md"), renamed);
const p = path.join(dir, "my sdd.md");
r = validateCli(p, "--since", c1);
t("validator --since: a renamed id is caught (path with spaces)", r.code === 1 && r.out.split("\n")[0] === `my sdd.md:1: section "Print the label": id "print-label" existed at ${c1} (line 42 there) and is gone. A rename must keep the id; if the part was removed on purpose, pass --removed print-label`, r.out.split("\n")[0]);
r = validateCli(p, "--since", c1, "--removed", "print-label");
t("validator --since: --removed acknowledges a deliberate deletion", r.code === 0 && r.out.trim() === "sdd ok; 8 sections", r.out.trim());
t("validator --since: --removed on an id that still exists is reported", validate(good, { oldText: good, since: "x", removed: ["stock"] }).out[0].msg === 'id "stock" is listed in --removed but still exists');
g("mv", "my sdd.md", "renamed.md"); g("commit", "-q", "-m", "rename the file");
r = validateCli(path.join(dir, "renamed.md"), "--since", c1);
t("validator --since: after the SDD file was renamed the old commit has no file at that path (exit 2)", r.code === 2 && /^cannot read renamed\.md at /.test(r.out), r.out.trim().slice(0, 80));
