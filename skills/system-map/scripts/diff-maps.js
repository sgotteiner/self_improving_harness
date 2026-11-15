// Compares two versions of a map box by box (by id, children excluded): identical / changed / added / removed.
// Usage: node diff-maps.js <before.html> <after.html>
const fs = require('fs');
function load(f) {
  const s = fs.readFileSync(f, 'utf8');
  const a = s.indexOf('const T=');
  const b = s.indexOf('/* ───────── index');
  const T = new Function(s.slice(a, b) + '; return T;')();
  const m = new Map();
  (function walk(n) { const { children, ...rest } = n; m.set(n.id, JSON.stringify(rest)); (children || []).forEach(walk); })(T);
  return m;
}
const [, , fb, fa] = process.argv;
const B = load(fb), A = load(fa);
const added = [...A.keys()].filter(k => !B.has(k));
const removed = [...B.keys()].filter(k => !A.has(k));
const changed = [...A.keys()].filter(k => B.has(k) && A.get(k) !== B.get(k));
const same = [...A.keys()].filter(k => B.has(k) && A.get(k) === B.get(k)).length;
console.log('boxes before/after:', B.size, A.size);
console.log('identical:', same, 'changed:', changed.length, 'added:', added.length, 'removed:', removed.length);
console.log('added:', added.join(', ') || '-');
console.log('changed:', changed.join(', ') || '-');
console.log('removed:', removed.join(', ') || '-');
