// Sibling order of the map generator: a chain follows `after`; the rest keeps file order.
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

module.exports = { ordered, inFlow };
