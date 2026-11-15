// validate(text, { oldText, since, removed }) -> { out, count }: every problem of an SDD as { line, title, msg }.
// The rules are listed in skills/sdd/SKILL.md section 5. Used by validate-sdd.js and sdd-to-map.js.
const { parse, list } = require("./sdd-parse");

// ids the map's page uses itself: "root" is the top box; "constructor" would clash with its id lookup tables
const RESERVED = ["root", "constructor"];
const EXT = "py|js|ts|md|json|html|sh|db|yml|yaml|txt|csv|sql|css|toml|ini|env";

// what a plain-words text must not hold (the `feature` of a ## section): digits, paths and file names, code names
function plainWordsProblems(t) {
  const found = [];
  if (/\d/.test(t)) found.push("digits");
  const tokens = t.split(/\s+/).map(w => w.replace(/^[("'“]+|[)"'”.,;:!?]+$/g, ""));
  const isPath = (w) => /^[A-Za-z]:[\\/]/.test(w) || (/[\\/]/.test(w) && /\.[A-Za-z]/.test(w)) || new RegExp(`\\w\\.(${EXT})$`, "i").test(w);
  if (tokens.some(isPath)) found.push("a path or file name");
  // code name: `backticks`, snake_case, name() or dotted.call(, camelCase with two or more lowercase letters before the hump (getUser; not iPhone, eBay, macOS)
  if (/`|\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b|\w+\(\)|\w+\.\w+\(|\b[a-z]{2,}[A-Z][a-z]+/.test(t)) found.push("a code name");
  return found;
}

function validate(text, { oldText = null, since = "", removed = [] } = {}) {
  const { sections, errors } = parse(text);
  const out = errors.map(e => ({ ...e }));
  const bad = (s, msg, key) => out.push({ line: (key && s.fieldLines[key]) || s.line, title: s.title, msg });
  const byId = new Map();
  for (const s of sections) {
    const f = s.fields;
    if (!f.id) bad(s, "has no id (every section needs `id: <stable-kebab-id>` right under its heading)");
    else if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(f.id)) bad(s, `id "${f.id}" is not kebab-case (lowercase words joined by -)`, "id");
    else if (RESERVED.includes(f.id)) bad(s, `id "${f.id}" is reserved (the map page uses it itself)`, "id");
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
    if (list(s.fields.related).includes(s.fields.id)) bad(s, `related names its own id "${s.fields.id}"`, "related");
    // a flow must not loop: follow `after` links
    const seen = new Set();
    let x = s;
    while (x && x.fields.after && byId.has(x.fields.after)) {
      if (seen.has(x.fields.id)) { bad(s, `after chain loops back through "${x.fields.id}"`, "after"); break; }
      seen.add(x.fields.id);
      x = byId.get(x.fields.after);
    }
    if (s.level === 2 && s.fields.feature) {
      const found = plainWordsProblems(s.fields.feature);
      if (found.length) bad(s, `top-level feature text has ${found.join(", ")} (plain words at the top; names, numbers and paths go from the second level down)`, "feature");
    }
  }
  if (oldText != null) {
    for (const o of parse(oldText).sections.filter(s => s.fields.id)) {
      if (!byId.has(o.fields.id) && !removed.includes(o.fields.id))
        out.push({ line: 1, title: o.title, msg: `id "${o.fields.id}" existed at ${since} (line ${o.line} there) and is gone. A rename must keep the id; if the part was removed on purpose, pass --removed ${o.fields.id}` });
    }
    for (const id of removed) if (byId.has(id)) out.push({ line: byId.get(id).line, title: byId.get(id).title, msg: `id "${id}" is listed in --removed but still exists` });
  }
  out.sort((a, b) => a.line - b.line);
  return { out, count: sections.length };
}

module.exports = { validate, plainWordsProblems, RESERVED };
