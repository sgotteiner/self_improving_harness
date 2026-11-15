// Tests of the SDD tools. Usage: node test-sdd.js   (exit 1 if any test fails)
// Validator: the good fixture passes; each broken fixture fails with the right message; --since catches a vanished id.
// Generator: output passes system-map's check-structure.js; two runs give identical bytes; changing one section's text
// changes exactly one box (diff-maps.js); a tracked SDD records its commit and refuses uncommitted changes.
const fs = require("fs"), os = require("os"), path = require("path");
const { spawnSync, execFileSync } = require("child_process");
const here = __dirname, fx = path.join(here, "fixtures");
const sys = path.join(here, "..", "..", "system-map", "scripts");
const run = (script, ...a) => { const r = spawnSync("node", [script, ...a], { encoding: "utf8" }); return { code: r.status, out: (r.stdout || "") + (r.stderr || "") }; };
const validate = (...a) => run(path.join(here, "validate-sdd.js"), ...a);
const gen = (...a) => run(path.join(here, "sdd-to-map.js"), ...a);
let failed = 0;
function t(name, ok, detail) { console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  | " + detail : ""}`); if (!ok) failed++; }

// ---- validator
let r = validate(path.join(fx, "good.md"));
t("validator: good fixture passes", r.code === 0, r.out.trim());
const broken = [
  ["broken-no-feature.md", /Check the stock.*lists criteria\/files but has no feature/],
  ["broken-duplicate-id.md", /duplicate id "check-stock"/],
  ["broken-dangling.md", /related names "ghost-feature"[\s\S]*after names "label-step"/],
  ["broken-top-level-detail.md", /top-level feature text has digits, a path or file name, a code name|top-level feature text has digits/],
];
for (const [f, re] of broken) {
  r = validate(path.join(fx, f));
  t(`validator: ${f} fails with the right message`, r.code === 1 && re.test(r.out), r.out.split("\n")[0]);
}
// a section with no id at all
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "sddtest-"));
fs.writeFileSync(path.join(tmp, "noid.md"), fs.readFileSync(path.join(fx, "good.md"), "utf8").replace("id: stock\n", ""));
r = validate(path.join(tmp, "noid.md"));
t("validator: a section without id fails", r.code === 1 && /Stock": has no id/.test(r.out), r.out.split("\n")[0]);

// ---- --since: an id that disappeared (rename without keeping the id)
const repo = path.join(tmp, "repo");
fs.mkdirSync(repo);
const g = (...a) => execFileSync("git", ["-C", repo, ...a], { encoding: "utf8" });
g("init", "-q"); g("config", "user.email", "t@example.invalid"); g("config", "user.name", "t");
const good = fs.readFileSync(path.join(fx, "good.md"), "utf8");
fs.writeFileSync(path.join(repo, "sdd.md"), good);
g("add", "sdd.md"); g("commit", "-q", "-m", "first");
const c1 = g("rev-parse", "HEAD").trim();
fs.writeFileSync(path.join(repo, "sdd.md"), good.replace("id: print-label", "id: label-printing").replace("after: print-label", "after: label-printing"));
r = validate(path.join(repo, "sdd.md"), "--since", c1);
t("validator --since: a renamed id is caught", r.code === 1 && /id "print-label" existed at .* and is gone/.test(r.out), r.out.split("\n")[0]);
r = validate(path.join(repo, "sdd.md"), "--since", c1, "--removed", "print-label");
t("validator --since: --removed acknowledges a deliberate deletion", r.code === 0, r.out.trim());
fs.writeFileSync(path.join(repo, "sdd.md"), good);

// ---- generator on the fixture outside git
const sdd = path.join(tmp, "good.md"), map1 = path.join(tmp, "map1.html"), map2 = path.join(tmp, "map2.html");
fs.copyFileSync(path.join(fx, "good.md"), sdd);
r = gen(sdd, map1);
t("generator: writes a map", r.code === 0, r.out.trim());
r = run(path.join(sys, "check-structure.js"), map1);
t("generator: output passes check-structure.js", r.code === 0 && /structure ok; 9 nodes/.test(r.out), r.out.trim());
gen(sdd, map2);
t("generator: twice gives identical bytes", fs.readFileSync(map1).equals(fs.readFileSync(map2)));
const T = new Function("const T=" + fs.readFileSync(map1, "utf8").split("const T=")[1].split("/* ───────── index")[0] + ";return T;")();
const find = (n, id) => n.id === id ? n : (n.children || []).map(c => find(c, id)).find(Boolean);
const order = (n) => (n.children || []).map(c => c.id).join(",");
t("generator: nesting and flow order follow the SDD", order(T) === "take-order,pack-send,stock" && order(find(T, "take-order")) === "check-stock,take-payment" && order(find(T, "pack-send")) === "print-label,hand-over" && find(T, "retry-payment") !== undefined, order(T));
t("generator: lanes (flow vs support), links, red note, file", T.children[0].lane === "flow" && T.children[2].lane === "support" && find(T, "check-stock").talks[0].to === "stock" && /^Open: /.test(find(T, "take-payment").note) && find(T, "retry-payment").file === "shop/payment.py");
// change one section's text -> exactly one box changes
fs.writeFileSync(sdd, fs.readFileSync(sdd, "utf8").replace("The customer pays; the order is created only after the payment is confirmed.", "The customer pays by card or by transfer; the order is created only after the payment is confirmed."));
const map3 = path.join(tmp, "map3.html");
gen(sdd, map3);
r = run(path.join(sys, "diff-maps.js"), map1, map3);
t("generator: changing one section changes exactly that box", /identical: 8 changed: 1 added: 0 removed: 0/.test(r.out) && /changed: take-payment/.test(r.out), r.out.split("\n").slice(1, 4).join(" / "));
// the map file's own rendering code survives a regeneration
const before = fs.readFileSync(map1, "utf8"), after = fs.readFileSync(map3, "utf8");
const tail = (s) => s.slice(s.indexOf("/* ───────── index"));
t("generator: rendering code outside T is untouched", tail(before) === tail(after) && before.slice(0, before.indexOf("const T=")) === after.slice(0, after.indexOf("const T=")));

// ---- generator inside git: records the commit, refuses uncommitted changes, --commit reads history
fs.writeFileSync(path.join(repo, "sdd.md"), good);
const mapg = path.join(tmp, "mapg.html");
r = gen(path.join(repo, "sdd.md"), mapg);
const T2 = new Function("const T=" + fs.readFileSync(mapg, "utf8").split("const T=")[1].split("/* ───────── index")[0] + ";return T;")();
t("generator: records sdd + sddCommit of a tracked, clean SDD", r.code === 0 && T2.sddCommit === c1 && T2.sdd[0] === "sdd.md", `sddCommit ${String(T2.sddCommit).slice(0, 10)}`);
fs.writeFileSync(path.join(repo, "sdd.md"), good + "\n## Extra\nid: extra\nfeature: Something new.\n");
r = gen(path.join(repo, "sdd.md"), path.join(tmp, "mapd.html"));
t("generator: refuses an SDD with uncommitted changes", r.code === 1 && /uncommitted changes/.test(r.out), r.out.split("\n")[0]);
const mapc = path.join(tmp, "mapc.html");
r = gen(path.join(repo, "sdd.md"), mapc, "--commit", c1);
t("generator --commit: draws the SDD as it was at that commit", r.code === 0 && fs.readFileSync(mapc, "utf8").includes(c1) && !fs.readFileSync(mapc, "utf8").includes('"extra"'), r.out.trim());

fs.rmSync(tmp, { recursive: true, force: true });
console.log(failed ? `\n${failed} FAILED` : "\nall tests passed");
process.exit(failed ? 1 : 0);
