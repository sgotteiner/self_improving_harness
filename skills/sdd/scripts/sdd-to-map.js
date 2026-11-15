// Writes the system map's data (the object T) from an SDD in the format of skills/sdd/SKILL.md. No agent, no guessing:
// the same SDD gives a byte-identical map.
// Usage: node sdd-to-map.js <sdd.md> <map.html> [--template <template.html>] [--commit <id>] [--dirty]
//   (default)        reads the working-tree SDD; it must have no uncommitted changes if it is tracked by git
//   --commit <id>    reads the SDD as it was at that commit (git show)
//   --dirty          allow uncommitted changes (sddCommit is then "uncommitted")
// If <map.html> exists only its T is replaced (its rendering code and text stay); otherwise it starts from the template.
// Boxes: one per section, nested like the headings. name = heading, desc = feature, facts = value, what/how, criteria
// lines, file = the files line, talks = related, order = after, note = open, sdd = the heading. Root: sdd, sddCommit.
const fs = require("fs");
const path = require("path");
const { parse, list, filesOf, show, git, repoPath } = require("./sdd-lib");

const args = process.argv.slice(2);
const flag = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : null; };
const pos = args.filter((a, i) => !a.startsWith("--") && !(i > 0 && ["--template", "--commit"].includes(args[i - 1])));
if (pos.length < 2) { console.error("usage: node sdd-to-map.js <sdd.md> <map.html> [--template t.html] [--commit id] [--dirty]"); process.exit(2); }
const sddFile = path.resolve(pos[0]), mapFile = path.resolve(pos[1]);
const template = flag("--template") || path.join(__dirname, "..", "..", "system-map", "assets", "template.html");
const commit = flag("--commit");

function fail(msg) { console.error(msg); process.exit(1); }

// ---- the SDD text and the commit it stands for
let text, sddCommit = null;
const rp = repoPath(sddFile);
if (commit) {
  try { text = show(sddFile, commit); sddCommit = git(sddFile, ["rev-parse", commit + "^{commit}"]); }
  catch (e) { fail(`cannot read ${path.basename(sddFile)} at ${commit}: ${String(e.stderr || e.message).trim()}`); }
} else {
  text = fs.readFileSync(sddFile, "utf8");
  let tracked = false;
  if (rp !== null) { try { git(sddFile, ["ls-files", "--error-unmatch", path.basename(sddFile)]); tracked = true; } catch (e) { /* untracked */ } }
  if (tracked) {
    const dirty = git(sddFile, ["status", "--porcelain", "--", path.basename(sddFile)]) !== "";
    if (dirty && !args.includes("--dirty")) fail(`${path.basename(sddFile)} has uncommitted changes: commit the SDD first (the map records the commit it was drawn from), or use --commit <id>, or --dirty`);
    sddCommit = dirty ? "uncommitted" : git(sddFile, ["log", "-1", "--format=%H", "--", path.basename(sddFile)]);
  }
}

// ---- parse and sanity-check (the full rules live in validate-sdd.js)
const { root, sections, errors } = parse(text);
if (errors.length) fail("the SDD has format errors (run validate-sdd.js):\n" + errors.map(e => `  line ${e.line}: ${e.title}: ${e.msg}`).join("\n"));
const seen = new Set();
for (const s of sections) {
  if (!s.fields.id || !s.fields.feature) fail(`section "${s.title}" (line ${s.line}) has no id or feature: run validate-sdd.js`);
  if (seen.has(s.fields.id)) fail(`duplicate id ${s.fields.id}: run validate-sdd.js`);
  seen.add(s.fields.id);
}

// ---- siblings in flow order: a chain follows `after`; the rest keeps file order
function ordered(kids) {
  const ids = new Set(kids.map(k => k.fields.id));
  const next = new Map();
  kids.forEach(k => { if (k.fields.after && ids.has(k.fields.after)) next.set(k.fields.after, k); });
  const out = [], placed = new Set();
  const place = (k) => { while (k && !placed.has(k)) { placed.add(k); out.push(k); k = next.get(k.fields.id); } };
  kids.forEach(k => { if (!(k.fields.after && ids.has(k.fields.after))) place(k); });
  kids.forEach(k => place(k));  // anything left (a loop) in file order
  return out;
}
const inFlow = (k, kids) => !!k.fields.after || kids.some(o => o.fields.after === k.fields.id);

function box(s, top, siblings) {
  const f = s.fields, kids = ordered(s.children);
  const flowKid = kids.some(k => inFlow(k, kids));
  const b = { id: f.id, name: s.title };
  if (top) b.lane = inFlow(s, siblings) ? "flow" : "support";
  if (f.tag) b.tag = f.tag;
  b.kind = inFlow(s, siblings) ? "step" : "group";
  b.desc = f.feature;
  const facts = [];
  if (f.value) facts.push("Value: " + f.value);
  s.body.forEach(p => facts.push(p));
  s.bullets.filter(x => !/^files?:/i.test(x.text)).forEach(x => facts.push(x.text));
  if (facts.length) b.facts = facts;
  const files = filesOf(s);
  if (files.length) b.file = files.join(", ");
  const rel = list(f.related);
  if (rel.length) b.talks = rel.map(to => ({ to, how: "related" }));
  if (f.open) b.note = "Open: " + f.open;
  b.sdd = s.title;
  if (flowKid) b.flow = true;
  if (kids.length) b.children = kids.map(k => box(k, false, kids));
  return b;
}

const top = ordered(root.children);
const T = { id: "root", name: root.title || path.basename(sddFile, ".md") };
if (root.fields.feature) T.desc = root.fields.feature;
T.sdd = [rp || path.basename(sddFile)];
if (sddCommit) T.sddCommit = sddCommit;
if (root.fields.open) T.note = "Open: " + root.fields.open;
T.children = top.map(k => box(k, true, top));

// ---- write: replace only T in the existing map (or in the template for a new map)
const MARK = "/* ───────── index";
const exists = fs.existsSync(mapFile);
let html = fs.readFileSync(exists ? mapFile : template, "utf8");
const a = html.indexOf("const T="), b = html.indexOf(MARK);
if (a < 0 || b < 0 || b < a) fail(`${exists ? mapFile : template} has no "const T=" ... "${MARK}" to replace`);
html = html.slice(0, a) + "const T=" + JSON.stringify(T, null, 1) + ";\n\n" + html.slice(b);
if (!exists) {
  const short = sddCommit && sddCommit !== "uncommitted" ? sddCommit.slice(0, 7) : null;
  html = html.split("SYSTEM NAME Map").join(T.name + " Map")
    .replace(/<p>ONE SENTENCE:[^<]*<\/p>/, () => `<p>${esc(T.desc || "")} Click any box to see how it works inside. Drawn from the SDD${short ? " at commit " + short : ""}.</p>`)
    .replace(/<footer>[^<]*<\/footer>/, "<footer>Drawn from the SDD by sdd-to-map.js. Items marked in red are open questions, not facts.</footer>")
    .replace("The pipeline · news to video", "The flow · in order")
    .replace("Shared services · used by every step", "Shared parts · used by the flow");
}
function esc(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
fs.writeFileSync(mapFile, html);
let n = 0; (function c(x) { n++; (x.children || []).forEach(c); })(T);
console.log(`map written: ${mapFile}; ${n} boxes${sddCommit ? "; sddCommit " + sddCommit.slice(0, 12) : ""}`);
