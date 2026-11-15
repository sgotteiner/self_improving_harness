// Shared parser for the SDD format (skills/sdd/SKILL.md): a markdown heading tree whose sections carry fields.
// parse(text) -> { title, root, sections, errors }. Each section: { level, title, line, fields, body, bullets,
// children, parent }. Used by validate-sdd.js and sdd-to-map.js; no dependencies.
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const FIELDS = ["id", "feature", "after", "related", "value", "open", "tag"];

function parse(text) {
  const lines = text.split(/\r?\n/);
  const errors = [];
  const root = { level: 1, title: "", line: 1, fields: {}, fieldLines: {}, body: [], bullets: [], children: [], parent: null, isRoot: true };
  const sections = [];
  const stack = [root];
  let cur = null, fence = false, i = 0;
  const heads = [];
  for (; i < lines.length; i++) {
    if (/^\s*```/.test(lines[i])) fence = !fence;
    const m = !fence && /^(#{1,6})\s+(.*?)\s*#*\s*$/.exec(lines[i]);
    if (m) heads.push({ idx: i, level: m[1].length, title: m[2] });
  }
  heads.forEach((h, k) => {
    const end = k + 1 < heads.length ? heads[k + 1].idx : lines.length;
    let s;
    if (h.level === 1 && !root.titled) { s = root; root.title = h.title; root.titled = true; root.line = h.idx + 1; }
    else {
      s = { level: h.level, title: h.title, line: h.idx + 1, fields: {}, fieldLines: {}, body: [], bullets: [], children: [], parent: null };
      while (stack.length > 1 && stack[stack.length - 1].level >= h.level) stack.pop();
      s.parent = stack[stack.length - 1];
      s.parent.children.push(s);
      stack.push(s);
      sections.push(s);
      if (s.level > 1 && s.parent.level < s.level - 1 && !s.parent.isRoot)
        errors.push({ line: s.line, title: s.title, msg: `heading jumps from level ${s.parent.level} to ${s.level}` });
      if (s.parent.isRoot && s.level > 2)
        errors.push({ line: s.line, title: s.title, msg: `top-level feature must be a level-2 heading (##), found level ${s.level}` });
    }
    // field block: the lines right under the heading up to the first blank line
    let j = h.idx + 1, key = null;
    for (; j < end && lines[j].trim() !== ""; j++) {
      const fm = /^([a-z]+):\s*(.*)$/.exec(lines[j]);
      if (fm) {
        key = fm[1];
        if (!FIELDS.includes(key)) errors.push({ line: j + 1, title: h.title, msg: `unknown field "${key}:" (fields: ${FIELDS.join(", ")})` });
        else if (key in s.fields) errors.push({ line: j + 1, title: h.title, msg: `field "${key}:" given twice` });
        else { s.fields[key] = fm[2].trim(); s.fieldLines[key] = j + 1; }
      } else if (key && /^\s+\S/.test(lines[j])) {
        s.fields[key] += " " + lines[j].trim();  // continuation of a field value: indented line
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

// git helpers: `file` is an absolute path of the SDD file
function git(file, args) {
  return execFileSync("git", ["-C", path.dirname(file), ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
}
function show(file, commit) {
  const prefix = git(file, ["rev-parse", "--show-prefix"]);
  return execFileSync("git", ["-C", path.dirname(file), "show", `${commit}:${prefix}${path.basename(file)}`], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
}
function repoPath(file) {
  try { return git(file, ["rev-parse", "--show-prefix"]) + path.basename(file); } catch (e) { return null; }
}

module.exports = { parse, list, filesOf, show, git, repoPath, FIELDS, fs };
