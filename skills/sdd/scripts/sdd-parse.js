// Parser for the SDD format (skills/sdd/SKILL.md): a markdown heading tree whose sections carry fields.
// parse(text) -> { title, root, sections, errors }. Each section: { level, title, line, fields, fieldLines, body,
// bullets, children, parent }. No dependencies.
const FIELDS = ["id", "feature", "after", "related", "value", "open", "tag"];
const ROOT_FIELDS = ["feature", "open"];  // the title (#) carries only these

// heading lines: outside code fences (``` or ~~~; closed by the same char, at least as long), after a leading frontmatter block
function findHeadings(lines) {
  let i = 0;
  if (/^---\s*$/.test(lines[0] || "")) {
    const end = lines.findIndex((l, k) => k > 0 && /^(---|\.\.\.)\s*$/.test(l));
    if (end > 0) i = end + 1;
  }
  const heads = [];
  let fence = null;  // { ch, len }
  for (; i < lines.length; i++) {
    const f = /^\s*(`{3,}|~{3,})(.*)$/.exec(lines[i]);
    if (fence) { if (f && f[1][0] === fence.ch && f[1].length >= fence.len && f[2].trim() === "") fence = null; continue; }
    if (f) { fence = { ch: f[1][0], len: f[1].length }; continue; }
    const m = /^(#{1,6})\s+(.*?)(?:\s+#+)?\s*$/.exec(lines[i]);  // a closing # run only after a space: "Learn C#" stays
    if (m) heads.push({ idx: i, level: m[1].length, title: m[2] });
  }
  return heads;
}

function parse(text) {
  const lines = text.split(/\r?\n/);
  const errors = [];
  const root = { level: 1, title: "", line: 1, fields: {}, fieldLines: {}, body: [], bullets: [], children: [], parent: null, isRoot: true };
  const sections = [];
  const stack = [root];
  const heads = findHeadings(lines);
  heads.forEach((h, k) => {
    const end = k + 1 < heads.length ? heads[k + 1].idx : lines.length;
    let s;
    if (h.level === 1) {
      if (root.titled) { errors.push({ line: h.idx + 1, title: h.title, msg: "second level-1 heading (#): the project title is the only # heading; sections start at ##" }); return; }
      s = root; root.title = h.title; root.titled = true; root.line = h.idx + 1;
    } else {
      s = { level: h.level, title: h.title, line: h.idx + 1, fields: {}, fieldLines: {}, body: [], bullets: [], children: [], parent: null };
      while (stack.length > 1 && stack[stack.length - 1].level >= h.level) stack.pop();
      s.parent = stack[stack.length - 1];
      s.parent.children.push(s);
      stack.push(s);
      sections.push(s);
      if (s.parent.isRoot ? s.level > 2 : s.parent.level < s.level - 1)
        errors.push({ line: s.line, title: s.title, msg: s.parent.isRoot ? `top-level feature must be a level-2 heading (##), found level ${s.level}` : `heading jumps from level ${s.parent.level} to ${s.level}` });
    }
    // field block: the lines right under the heading up to the first blank line
    let j = h.idx + 1, key = null;
    for (; j < end && lines[j].trim() !== ""; j++) {
      const fm = /^([a-z]+):\s*(.*)$/.exec(lines[j]);
      if (fm) {
        key = fm[1];
        if (!FIELDS.includes(key)) errors.push({ line: j + 1, title: h.title, msg: `unknown field "${key}:" (fields: ${FIELDS.join(", ")})` });
        else if (s.isRoot && !ROOT_FIELDS.includes(key)) errors.push({ line: j + 1, title: h.title, msg: `the title (#) may carry only ${ROOT_FIELDS.join(" and ")}, not "${key}:"` });
        else if (key in s.fields) errors.push({ line: j + 1, title: h.title, msg: `field "${key}:" given twice` });
        else { s.fields[key] = fm[2].trim(); s.fieldLines[key] = j + 1; }
      } else if (key && /^\s+\S/.test(lines[j])) {
        if (key in s.fields) s.fields[key] += " " + lines[j].trim();  // continuation of a field value: indented line
      } else {
        errors.push({ line: j + 1, title: h.title, msg: `line under the heading is not a field: "${lines[j].trim().slice(0, 50)}" (fields end at the first blank line)` });
      }
    }
    // body: paragraphs and bullets
    let para = [], bullet = null;
    const flush = () => { if (para.length) s.body.push(para.join(" ")); para = []; };
    for (; j < end; j++) {
      const l = lines[j];
      if (l.trim() === "") { flush(); bullet = null; continue; }
      const b = /^[-*]\s+(.*)$/.exec(l);
      if (b) { flush(); bullet = { text: b[1].trim(), line: j + 1 }; s.bullets.push(bullet); }
      else if (bullet && /^\s+\S/.test(l)) bullet.text += " " + l.trim();
      else { bullet = null; para.push(l.trim()); }
    }
    flush();
  });
  return { title: root.title, root, sections, errors };
}

const list = (v) => (v || "").split(",").map(x => x.trim()).filter(Boolean);

function filesOf(s) {
  const b = s.bullets.find(x => /^files?:/i.test(x.text));
  return b ? list(b.text.replace(/^files?:/i, "")) : [];
}

module.exports = { parse, list, filesOf, FIELDS };
