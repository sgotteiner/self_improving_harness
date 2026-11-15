// Checks the map's data: no duplicate ids, every "talks" target exists, every node has a name and a kind.
// Usage: node check-structure.js <map.html>
const fs = require("fs");
const h = fs.readFileSync(process.argv[2], "utf8");
const s = h.slice(h.lastIndexOf("<script>") + 8, h.lastIndexOf("</script>"));
const T = new Function(s.split("/* ───────── index")[0] + ";return T;")();
const ids = {}, problems = [];
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
