// Checks the map: the page is sound, no duplicate ids, every "talks" target exists, every node has a name.
// Usage: node check-structure.js <map.html>
const fs = require("fs");
const { readT, pageProblems } = require("./map-data");
const h = fs.readFileSync(process.argv[2], "utf8");
let T;
const ids = Object.create(null), problems = [];
try { problems.push(...pageProblems(h)); T = readT(h); } catch (e) { console.log("cannot read the map: " + e.message); process.exit(1); }
(function w(x) {
  if (ids[x.id]) problems.push("duplicate id " + x.id);
  ids[x.id] = x;
  if (x.id !== "root" && !x.name) problems.push("no name: " + x.id);
  (x.children || []).forEach(w);
})(T);
(function w(x) {
  (x.talks || []).forEach(t => { if (!ids[t.to]) problems.push(`talks target missing: ${x.id} -> ${t.to}`); });
  (x.children || []).forEach(w);
})(T);
console.log(problems.length ? problems.join("\n") : `structure ok; ${Object.keys(ids).length} nodes`);
process.exit(problems.length ? 1 : 0);
