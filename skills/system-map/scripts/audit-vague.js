// Lists map nodes that say something is checked/scored/filtered/etc. but give no number, no quoted example
// and no named criterion (an env var, a Redis key or a snake_case label).
// A vague node that has a `note` (what is unknown) is listed apart, not counted as a failure.
// Usage: node audit-vague.js <map.html>
const fs = require("fs");
const h = fs.readFileSync(process.argv[2], "utf8");
const s = h.slice(h.lastIndexOf("<script>") + 8, h.lastIndexOf("</script>"));
const T = new Function(s.split("/* ───────── index")[0] + ";return T;")();
const VERBS = /\b(check(s|ed|ing)?|verif(y|ies|ied|ying)|scor(e|es|ed|ing)|filter(s|ed|ing)?|classif(y|ies|ied|ying)|rank(s|ed|ing)?|skip(s|ped|ping)?|limit(s|ed|ing)?|cap(s|ped)?|rout(e|es|ed|ing)|retr(y|ies|ied)|approv(e|es|ed|ing|al)|merg(e|es|ed|ing)|dedup\w*|duplicates?|deduplicat\w*|label(s|led)?|decid(e|es|ed)|drop(s|ped)?|block(s|ed)?|flag(s|ged)?|reject(s|ed)?)\b/i;
const NUM = /\d/;
const QUOTE = /[“”"]/;
const NAMED = /\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b|\b[a-z]+_[a-z_]+\b|\w+:<|<\w+>/;
const bad = [], noted = [], thin = [];
let n = 0;
(function w(x) {
  n++;
  const text = [x.desc || "", ...(x.facts || [])].join(" \n ");
  if (x.id !== "root" && VERBS.test(text) && !NUM.test(text) && !QUOTE.test(text) && !NAMED.test(text)) (x.note ? noted : bad).push(`${x.id}: ${x.name}`);
  // second measure: names an action word but has no facts list and nothing inside to open
  if (x.id !== "root" && VERBS.test(text) && !(x.facts || []).length && !(x.children || []).length && !x.note) thin.push(`${x.id}: ${x.name}`);
  (x.children || []).forEach(w);
})(T);
console.log(`nodes ${n}; vague ${bad.length}; vague but noted ${noted.length}`);
bad.forEach(b => console.log("  VAGUE " + b));
noted.forEach(b => console.log("  noted " + b));
console.log(`thin (action word, no facts, no children, no note): ${thin.length}`);
thin.forEach(b => console.log("  THIN " + b));
