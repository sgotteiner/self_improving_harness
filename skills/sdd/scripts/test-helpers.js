// Shared by the test files of test-sdd.js: running the CLIs, a git repo, a temp dir, the pass/fail counter.
const fs = require("fs"), os = require("os"), path = require("path");
const { spawnSync, execFileSync } = require("child_process");
const here = __dirname;
const fx = path.join(here, "fixtures");
const sys = path.join(here, "..", "..", "system-map", "scripts");
const run = (script, ...a) => { const r = spawnSync("node", [script, ...a], { encoding: "utf8" }); return { code: r.status, out: (r.stdout || "") + (r.stderr || "") }; };
const validateCli = (...a) => run(path.join(here, "validate-sdd.js"), ...a);
const gen = (...a) => run(path.join(here, "sdd-to-map.js"), ...a);
const check = (map) => run(path.join(sys, "check-structure.js"), map);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "sddtest-"));
const good = fs.readFileSync(path.join(fx, "good.md"), "utf8");
const write = (name, text) => { const p = path.join(tmp, name); fs.writeFileSync(p, text); return p; };
const read = (p) => fs.readFileSync(p, "utf8");
let failed = 0, total = 0;
function t(name, ok, detail) { total++; console.log(`${ok ? "PASS" : "FAIL"}  ${name}${!ok && detail ? "  | " + detail : ""}`); if (!ok) failed++; }
function repo(name) {
  const dir = path.join(tmp, name);
  fs.mkdirSync(dir);
  const g = (...a) => execFileSync("git", ["-C", dir, ...a], { encoding: "utf8" }).trim();
  g("init", "-q"); g("config", "user.email", "t@example.invalid"); g("config", "user.name", "t"); g("config", "core.autocrlf", "false");
  return { dir, g };
}
const summary = () => { console.log(failed ? `\n${failed} of ${total} FAILED` : `\nall ${total} tests passed`); fs.rmSync(tmp, { recursive: true, force: true }); process.exit(failed ? 1 : 0); };

module.exports = { fs, path, here, fx, sys, run, validateCli, gen, check, tmp, good, write, read, t, repo, summary };
