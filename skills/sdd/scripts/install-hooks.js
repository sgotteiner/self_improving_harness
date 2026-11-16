// Installs the SDD git hooks (sdd-hook.js) into the repo that holds an SDD.
// Usage: node install-hooks.js <any path inside the repo>
// All or nothing: both hooks are checked first; if either file exists and is not ours, nothing is written and the line to add
// by hand is printed. The installed hook fails open: it exits 0 when node or sdd-hook.js is missing, and refuses a commit only
// when sdd-hook.js says so (exit code 3 = the SDD fails the validator).
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const git = (dir, ...a) => execFileSync("git", ["-C", dir, ...a], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
const target = path.resolve(process.argv[2] || ".");
const dir = fs.existsSync(target) && fs.statSync(target).isDirectory() ? target : path.dirname(target);
let hooks;
try { hooks = path.resolve(dir, git(dir, "rev-parse", "--git-path", "hooks")); } catch (e) { console.error(`${dir} is not in a git repository: no hooks to install`); process.exit(2); }
const script = path.join(__dirname, "sdd-hook.js").replace(/\\/g, "/");
const modes = ["pre-commit", "post-commit"];
const text = (mode) => `#!/bin/sh
# SDD hook (skills/sdd/SKILL.md section 6): validates the SDD before a commit, redraws its map after. Fails open.
script="${script}"
command -v node >/dev/null 2>&1 && [ -f "$script" ] || exit 0
node "$script" ${mode}
[ $? -eq 3 ] && exit 1
exit 0
`;
const foreign = modes.map(m => path.join(hooks, m)).filter(f => fs.existsSync(f) && !fs.readFileSync(f, "utf8").includes("sdd-hook.js"));
if (foreign.length) {
  foreign.forEach(f => console.error(`foreign hook present: ${f}: add the line 'node "${script}" ${path.basename(f)}' to it by hand (nothing was installed)`));
  process.exit(1);
}
fs.mkdirSync(hooks, { recursive: true });
for (const m of modes) {
  fs.writeFileSync(path.join(hooks, m), text(m), { mode: 0o755 });
  console.log(`installed ${path.join(hooks, m)}`);
}
