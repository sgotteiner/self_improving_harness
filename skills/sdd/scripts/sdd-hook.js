// Git hooks for the repo of an SDD (installed by install-hooks.js), so nothing depends on anyone remembering:
//   pre-commit   an SDD in the commit must pass the validator (the same rules as validate-sdd.js, with --since HEAD), else the
//                commit is refused with exit code 3. A part removed on purpose: SDD_REMOVED=id,id git commit ...
//   post-commit  a commit that changed an SDD regenerates the map(s) drawn from it (sdd-to-map.js --commit HEAD) and commits
//                them as their own commit ("Map follows the SDD"). An SDD that fails the validator is never drawn. A map commit
//                that fails is unstaged again, so the next commit does not carry a stray map.
// Fails open: only a validator finding refuses a commit (exit 3, which the installed hook turns into 1). Any internal error
// is printed and the commit goes through (exit 0): a broken tool must never block his work.
// Switches in the setup's slots.json (SDD_SLOTS overrides the path): `sdd-commit-check` (pre-commit), `map-follows-sdd` (post-commit).
// Which files are SDDs: those named in the `sdd` list of a map of the repo (sdd-maps.js).
const fs = require("fs");
const path = require("path");
const { spawnSync, execFileSync } = require("child_process");

const REFUSE = 3;
const mode = process.argv[2];
const slots = process.env.SDD_SLOTS || path.join(__dirname, "..", "..", "..", "slots.json");
const on = (name) => { try { return JSON.parse(fs.readFileSync(slots, "utf8"))[name].enabled === true; } catch (e) { return false; } };
const git = (...a) => execFileSync("git", a, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
const lines = (s) => s.split("\0").filter(Boolean);

function preCommit(repo, maps) {
  const { validate, list } = require("./sdd-lib");
  const sdds = new Set(maps(repo).flatMap(m => m.sdd));
  const staged = lines(git("diff", "--cached", "--name-only", "-z", "--diff-filter=AM")).filter(f => sdds.has(f));
  let bad = 0;
  for (const f of staged) {
    let old = null;
    try { old = git("show", "HEAD:" + f); } catch (e) { /* a new file */ }
    const { out } = validate(git("show", ":" + f), { oldText: old, since: "HEAD", removed: list(process.env.SDD_REMOVED) });
    out.forEach(p => console.error(`${f}:${p.line}: section "${p.title}": ${p.msg}`));
    bad += out.length ? 1 : 0;
  }
  if (bad) console.error("commit refused: the SDD must pass the validator (skills/sdd/SKILL.md section 5)");
  return bad ? REFUSE : 0;
}

function postCommit(repo, maps) {
  const changed = lines(git("diff-tree", "--no-commit-id", "--name-only", "-r", "-z", "--root", "HEAD"));
  const head = git("rev-parse", "HEAD").trim();
  for (const m of maps(repo).filter(m => m.sdd.some(s => changed.includes(s)))) {
    if (m.sdd.length !== 1) { console.error(`map ${m.rel}: not regenerated, it lists ${m.sdd.length} SDD files (the generator reads one)`); continue; }
    const r = spawnSync("node", [path.join(__dirname, "sdd-to-map.js"), path.join(repo, m.sdd[0]), m.file, "--commit", "HEAD"], { encoding: "utf8" });
    if (r.status !== 0) { console.error(`map ${m.rel}: not regenerated\n${r.stdout}${r.stderr}`); continue; }
    if (!git("status", "--porcelain", "--", m.rel).trim()) continue;
    try {
      git("add", "--", m.rel);
      git("commit", "-q", "-m", `Map follows the SDD: ${m.rel} regenerated from ${head.slice(0, 7)}`, "--", m.rel);
      console.log(`map ${m.rel} regenerated from the SDD at ${head.slice(0, 7)}`);
    } catch (e) {
      try { git("reset", "-q", "--", m.rel); } catch (e2) { /* nothing staged */ }
      console.error(`map ${m.rel}: the map commit failed, the map is unstaged (${String(e.stderr || e.message).trim()})`);
    }
  }
  return 0;
}

let code = 0;
try {
  const check = mode === "pre-commit" ? "sdd-commit-check" : mode === "post-commit" ? "map-follows-sdd" : null;
  if (check && on(check)) {
    const repo = git("rev-parse", "--show-toplevel").trim();
    process.chdir(repo);
    code = (mode === "pre-commit" ? preCommit : postCommit)(repo, require("./sdd-maps").maps);
  }
} catch (e) {
  console.error(`sdd-hook ${mode}: internal error, not blocking: ${e && e.message}`);
  code = 0;
}
process.exit(code);
