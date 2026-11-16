// End-to-end tests of the git hooks (sdd-hook.js, install-hooks.js) in a temp git repo: a valid SDD commit redraws the map
// (only the changed box changes), an invalid SDD is refused and never drawn, the switches, the override, the foreign hook.
const { fs, path, here, sys, good, tmp, write, read, t, repo, run } = require("./test-helpers");
const { spawnSync } = require("child_process");
const { readT } = require("../../system-map/scripts/map-data");

const slots = (a, b) => write("slots.json", JSON.stringify({ "map-follows-sdd": { enabled: a }, "sdd-commit-check": { enabled: b } }));
const { dir, g } = repo("hooks repo");
const commit = (msg, env = {}) => {
  const r = spawnSync("git", ["-C", dir, "commit", "-q", "-am", msg],
    { encoding: "utf8", env: { ...process.env, SDD_SLOTS: path.join(tmp, "slots.json"), ...env } });
  return { code: r.status, out: (r.stdout || "") + (r.stderr || "") };
};
const sdd = path.join(dir, "sdd.md"), map = path.join(dir, "map.html");
slots(true, true);
fs.writeFileSync(sdd, good);
g("add", "."); g("commit", "-q", "-m", "first");
let r = run(path.join(here, "sdd-to-map.js"), sdd, map);
g("add", "."); g("commit", "-q", "-m", "map");
const before = path.join(tmp, "before.html");
fs.copyFileSync(map, before);
const count = () => Number(g("rev-list", "--count", "HEAD"));
r = run(path.join(here, "install-hooks.js"), dir);
t("install: writes both hooks", r.code === 0 && fs.existsSync(path.join(dir, ".git", "hooks", "pre-commit")) && fs.existsSync(path.join(dir, ".git", "hooks", "post-commit")), r.out);

// ---- a valid SDD commit redraws the map from the new commit; only the changed section's box changes
fs.writeFileSync(sdd, good.replace("The customer pays; the order is created only after the payment is confirmed.", "The customer pays by card or by transfer; the order is created only after the payment is confirmed."));
const n = count();
r = commit("change payment");
const sddCommit = g("rev-parse", "HEAD~1");
t("post-commit: a valid SDD commit adds one map commit", r.code === 0 && count() === n + 2 && /^Map follows the SDD/.test(g("log", "-1", "--format=%s")), r.out);
r = run(path.join(sys, "diff-maps.js"), before, map);
// the root box records the new sddCommit, so it changes with the section's box; no other box does
t("post-commit: only the changed section's box (and the root's sddCommit) changed", /identical: 7 changed: 2 added: 0 removed: 0/.test(r.out) && /changed: root, take-payment/.test(r.out), r.out.trim());
t("post-commit: the map records the new SDD commit", readT(read(map)).sddCommit === sddCommit && g("status", "--porcelain") === "");

// ---- an invalid SDD is refused; nothing is drawn
fs.writeFileSync(sdd, read(sdd).replace("id: stock\n", "id: take-payment\n"));
const head = g("rev-parse", "HEAD");
r = commit("break it");
t("pre-commit: an invalid SDD is refused with the validator's lines", r.code !== 0 && /duplicate id/.test(r.out) && /commit refused/.test(r.out) && g("rev-parse", "HEAD") === head, r.out.slice(0, 200));
g("checkout", "--", "sdd.md");

// ---- a removed part needs SDD_REMOVED; with it the commit and the redraw go through
fs.writeFileSync(sdd, read(sdd).replace(/\n## Stock[\s\S]*$/, "\n").replace(/^related: stock\n/gm, "").replace(/ — diary: .*$/gm, ""));
r = commit("remove stock");
t("pre-commit: a part gone without SDD_REMOVED is refused", r.code !== 0 && /existed at HEAD/.test(r.out), r.out.slice(0, 200));
r = commit("remove stock", { SDD_REMOVED: "stock" });
t("pre-commit: SDD_REMOVED lets a deliberate removal through", r.code === 0 && !readT(read(map)).children.some(c => c.id === "stock"), r.out.slice(0, 200));

// ---- the switches
slots(true, false);
fs.writeFileSync(sdd, read(sdd) + "\n## Broken\nid: take-payment\nfeature: x\n");
const mapBefore = read(map), n2 = count();
r = commit("no check");
t("switch sdd-commit-check off: the commit goes through, but the invalid SDD is not drawn (the map stays)", r.code === 0 && read(map) === mapBefore && count() === n2 + 1 && /not regenerated/.test(r.out), r.out.slice(0, 250));
slots(false, true);
fs.writeFileSync(sdd, good);
r = commit("valid again, map switch off");
t("switch map-follows-sdd off: no map commit", r.code === 0 && count() === n2 + 2 && read(map) === mapBefore, r.out.slice(0, 200));

// ---- the installer: all or nothing, never over a hook that is not ours, nothing outside a git repo
const { dir: d2 } = repo("foreign");
fs.mkdirSync(path.join(d2, ".git", "hooks"), { recursive: true });
fs.writeFileSync(path.join(d2, ".git", "hooks", "post-commit"), "#!/bin/sh\necho mine\n");
r = run(path.join(here, "install-hooks.js"), d2);
t("install: a foreign hook is kept, nothing is half installed, the line to add by hand is printed",
  r.code === 1 && /foreign hook present/.test(r.out) && /by hand/.test(r.out) && read(path.join(d2, ".git", "hooks", "post-commit")).includes("echo mine") && !fs.existsSync(path.join(d2, ".git", "hooks", "pre-commit")), r.out);
r = run(path.join(here, "install-hooks.js"), path.join(tmp, "not-a-repo-dir-" + process.pid));
t("install: outside a git repo it says so and installs nothing", r.code === 2 && /not in a git repository/.test(r.out), r.out);

// ---- fail open: only a validator finding refuses a commit
const hook = path.join(dir, ".git", "hooks", "pre-commit");
const direct = (cwd, m) => { const x = spawnSync("node", [path.join(here, "sdd-hook.js"), m], { cwd, encoding: "utf8", env: { ...process.env, SDD_SLOTS: path.join(tmp, "slots.json") } }); return { code: x.status, out: (x.stdout || "") + (x.stderr || "") }; };
const broken = good.replace("id: stock\n", "id: take-payment\n");
slots(true, true);
fs.writeFileSync(sdd, broken);
g("add", "sdd.md");
r = direct(dir, "pre-commit");
t("pre-commit: a validator finding exits 3 (the installed hook turns that into a refusal)", r.code === 3 && /commit refused/.test(r.out), r.out);
r = direct(tmp, "pre-commit");
t("pre-commit: an internal error (not in a repo) is printed and exits 0, never blocks", r.code === 0 && /internal error, not blocking/.test(r.out), r.out);
const text = read(hook);
fs.writeFileSync(hook, text.replace(/script="[^"]*"/, 'script="/no/such/sdd-hook.js"'));
r = commit("hook script missing");
t("installed hook: a missing sdd-hook.js exits 0, the commit goes through even with an invalid SDD", r.code === 0, r.out.slice(0, 200));
fs.writeFileSync(hook, text.replace("command -v node", "command -v no-such-node-binary"));
fs.writeFileSync(sdd, broken + "\n");
r = commit("node missing");
t("installed hook: node missing exits 0, the commit goes through", r.code === 0, r.out.slice(0, 200));
fs.writeFileSync(hook, text);
r = direct(dir, "post-commit");
t("post-commit: an invalid SDD in HEAD never makes it fail", r.code === 0, r.out);

// ---- a failed map commit unstages the map
fs.writeFileSync(sdd, good);
slots(true, false);
fs.writeFileSync(path.join(dir, ".git", "hooks", "commit-msg"), '#!/bin/sh\ncase "$(cat "$1")" in "Map follows"*) exit 1;; esac\nexit 0\n', { mode: 0o755 });
r = commit("valid again");
fs.writeFileSync(sdd, good.replace("The customer pays;", "The customer pays at once;"));
r = commit("change again");
t("post-commit: a failed map commit unstages the map and says so", r.code === 0 && /the map commit failed, the map is unstaged/.test(r.out) && g("diff", "--cached", "--name-only") === "", r.out.slice(0, 250));
