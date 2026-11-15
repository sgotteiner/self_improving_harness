// Validates an SDD file against the format in skills/sdd/SKILL.md.
// Usage: node validate-sdd.js <sdd.md> [--since <commit>] [--removed <id,id>]
//   --since <commit>   ids that existed in the file at that commit must still exist (a rename keeps the id)
//   --removed <ids>    ids deleted on purpose since that commit (the part was removed from the project)
// Prints one line per problem: <file>:<line>: section "<heading>": <message>. Exit 1 if any problem.
const fs = require("fs");
const path = require("path");
const { parse, list, show } = require("./sdd-lib");

const args = process.argv.slice(2);
const flag = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : null; };
const file = args.find((a, i) => !a.startsWith("--") && !(i > 0 && args[i - 1].startsWith("--")));
if (!file) { console.error("usage: node validate-sdd.js <sdd.md> [--since <commit>] [--removed <id,id>]"); process.exit(2); }
const abs = path.resolve(file);
const since = flag("--since"), removed = list(flag("--removed"));

function validate(text, oldText) {
  const { sections, errors } = parse(text);
  const out = errors.map(e => ({ ...e }));
  const bad = (s, msg, key) => out.push({ line: (key && s.fieldLines[key]) || s.line, title: s.title, msg });
  const byId = new Map();
  for (const s of sections) {
    const f = s.fields;
    if (!f.id) bad(s, "has no id (every section needs `id: <stable-kebab-id>` right under its heading)");
    else if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(f.id)) bad(s, `id "${f.id}" is not kebab-case (lowercase words joined by -)`, "id");
    else if (byId.has(f.id)) bad(s, `duplicate id "${f.id}" (also on "${byId.get(f.id).title}", line ${byId.get(f.id).line})`, "id");
    else byId.set(f.id, s);
    if (!f.feature) {
      if (s.bullets.length && !s.body.length) bad(s, "lists criteria/files but has no feature or what/how above them (details need a feature above)");
      else bad(s, "has no feature (say in plain words what it is / what happens here)");
    }
  }
  for (const s of sections) {
    for (const k of ["related", "after"]) {
      for (const id of list(s.fields[k])) if (!byId.has(id)) bad(s, `${k} names "${id}", which is not an id in this file`, k);
    }
    // a flow must not loop: follow `after` links
    const seen = new Set();
    let x = s;
    while (x && x.fields.after && byId.has(x.fields.after)) {
      if (seen.has(x.fields.id)) { bad(s, `after chain loops back through "${x.fields.id}"`, "after"); break; }
      seen.add(x.fields.id);
      x = byId.get(x.fields.after);
    }
    // top level: plain words only
    if (s.level === 2 && s.fields.feature) {
      const t = s.fields.feature;
      const found = [];
      if (/\d/.test(t)) found.push("digits");
      if (/[\w.-]+[\\/][\w.-]+|\b\w+\.(py|js|ts|md|json|html|sh|db|yml|yaml|txt)\b/.test(t)) found.push("a path or file name");
      if (/`|\b[a-z]+_[a-z0-9_]+\b|\b[a-z]+[A-Z]\w*\b|\w+\(\)/.test(t)) found.push("a code name");
      if (found.length) bad(s, `top-level feature text has ${found.join(", ")} (plain words at the top; names, numbers and paths go from the second level down)`, "feature");
    }
  }
  if (oldText != null) {
    const old = parse(oldText).sections.filter(s => s.fields.id);
    for (const o of old) {
      if (!byId.has(o.fields.id) && !removed.includes(o.fields.id))
        out.push({ line: 1, title: o.title, msg: `id "${o.fields.id}" existed at ${since} (line ${o.line} there) and is gone. A rename must keep the id; if the part was removed on purpose, pass --removed ${o.fields.id}` });
    }
    for (const id of removed) if (byId.has(id)) out.push({ line: byId.get(id).line, title: byId.get(id).title, msg: `id "${id}" is listed in --removed but still exists` });
  }
  return { out, count: sections.length };
}

let old = null;
if (since) {
  try { old = show(abs, since); } catch (e) { console.error(`cannot read ${path.basename(abs)} at ${since}: ${String(e.stderr || e.message).trim()}`); process.exit(2); }
}
const { out, count } = validate(fs.readFileSync(abs, "utf8"), old);
out.sort((a, b) => a.line - b.line);
if (out.length) {
  for (const p of out) console.log(`${path.basename(abs)}:${p.line}: section "${p.title}": ${p.msg}`);
  console.log(`${out.length} problem${out.length > 1 ? "s" : ""}`);
  process.exit(1);
}
console.log(`sdd ok; ${count} sections`);
