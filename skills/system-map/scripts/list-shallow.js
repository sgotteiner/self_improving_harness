// Lists leaf nodes with no facts list and a short description (under 160 characters), for a manual depth review.
// Usage: node list-shallow.js <map.html>
const fs = require("fs");
const h = fs.readFileSync(process.argv[2], "utf8");
const s = h.slice(h.lastIndexOf("<script>") + 8, h.lastIndexOf("</script>"));
const T = new Function(s.split("/* ───────── index")[0] + ";return T;")();
const out = [];
(function w(x, path) {
  const leaf = !(x.children || []).length;
  if (x.id !== "root" && leaf && !(x.facts || []).length && !x.note && (x.desc || "").length < 160 && !/^rule-|^cat-/.test(x.id)) out.push(`${x.id} (${(x.desc || "").length}): ${x.name} — ${(x.desc || "").slice(0, 110)}`);
  (x.children || []).forEach(c => w(c, path + "/" + x.id));
})(T, "");
console.log(out.length + " shallow leaves");
out.forEach(o => console.log("  " + o));
