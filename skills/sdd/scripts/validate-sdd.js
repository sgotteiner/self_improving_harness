// Validates an SDD file against the format in skills/sdd/SKILL.md.
// Usage: node validate-sdd.js <sdd.md> [--since <commit>] [--removed <id,id>]
//   --since <commit>   ids that existed in the file (same path) at that commit must still exist (a rename keeps the id)
//   --removed <ids>    ids deleted on purpose since that commit (the part was removed from the project)
// Prints one line per problem: <file>:<line>: section "<heading>": <message>. Exit 1 if any problem, 2 on bad usage.
const fs = require("fs");
const path = require("path");
const { validate, list, show } = require("./sdd-lib");

const args = process.argv.slice(2);
const flag = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : null; };
const file = args.find((a, i) => !a.startsWith("--") && !(i > 0 && args[i - 1].startsWith("--")));
if (!file) { console.error("usage: node validate-sdd.js <sdd.md> [--since <commit>] [--removed <id,id>]"); process.exit(2); }
const abs = path.resolve(file);
const since = flag("--since"), removed = list(flag("--removed"));

let oldText = null;
if (since) {
  try { oldText = show(abs, since); } catch (e) { console.error(`cannot read ${path.basename(abs)} at ${since}: ${String(e.stderr || e.message).trim()}`); process.exit(2); }
}
const { out, count } = validate(fs.readFileSync(abs, "utf8"), { oldText, since, removed });
if (out.length) {
  for (const p of out) console.log(`${path.basename(abs)}:${p.line}: section "${p.title}": ${p.msg}`);
  console.log(`${out.length} problem${out.length > 1 ? "s" : ""}`);
  process.exit(1);
}
console.log(`sdd ok; ${count} sections`);
