// Generator tests: determinism, one-box diffs, git (commit, uncommitted, --dirty, untracked, --commit), the validator gate.
const { fs, path, sys, run, gen, check, tmp, good, write, read, t, repo } = require("./test-helpers");
const { readT, MARK } = require("../../system-map/scripts/map-data");
const find = (n, id) => n.id === id ? n : (n.children || []).map(c => find(c, id)).find(Boolean);
const order = (n) => (n.children || []).map(c => c.id).join(",");

const sdd = write("good.md", good), map1 = path.join(tmp, "map1.html"), map2 = path.join(tmp, "map2.html");
let r = gen(sdd, map1);
t("generator: writes a map (untracked SDD says so, no sddCommit)", r.code === 0 && r.out.trim() === `map written: ${map1}; 9 boxes; the SDD is not tracked by git: no sddCommit` && readT(read(map1)).sddCommit === undefined, r.out.trim());
r = check(map1);
t("generator: output passes check-structure.js", r.code === 0 && r.out.trim() === "structure ok; 9 nodes", r.out.trim());
gen(sdd, map2);
t("generator: twice gives identical bytes", fs.readFileSync(map1).equals(fs.readFileSync(map2)));
const T = readT(read(map1));
t("generator: nesting and flow order follow the SDD", order(T) === "take-order,pack-send,stock" && order(find(T, "take-order")) === "check-stock,take-payment" && order(find(T, "pack-send")) === "print-label,hand-over" && find(T, "retry-payment") !== undefined, order(T));
t("generator: lanes, links, red note, file", T.children[0].lane === "flow" && T.children[2].lane === "support" && find(T, "check-stock").talks[0].to === "stock" && find(T, "take-payment").note === "Open: whether a partly paid order should be kept is not known" && find(T, "retry-payment").file === "shop/payment.py");
fs.writeFileSync(sdd, good.replace("The customer pays; the order is created only after the payment is confirmed.", "The customer pays by card or by transfer; the order is created only after the payment is confirmed."));
const map3 = path.join(tmp, "map3.html");
gen(sdd, map3);
r = run(path.join(sys, "diff-maps.js"), map1, map3);
t("generator: changing one section changes exactly that box", r.out.trim() === "boxes before/after: 9 9\nidentical: 8 changed: 1 added: 0 removed: 0\nadded: -\nchanged: take-payment\nremoved: -", r.out.trim());
const tail = (s) => s.slice(s.lastIndexOf(MARK));
t("generator: rendering code outside T is untouched", tail(read(map1)) === tail(read(map3)));

// ---- the validator gates the generator: nothing is written
const gate = (name, text, want) => {
  const out = path.join(tmp, name + ".html");
  const x = gen(write(name + ".md", text), out);
  t(`generator: refuses an SDD that fails the validator (${name})`, x.code === 1 && x.out.includes(want) && !fs.existsSync(out), x.out.trim().slice(0, 150));
};
gate("reserved", good.replace("id: stock", "id: root").replace(/related: stock/g, "related: root"), 'id "root" is reserved');
gate("kebab", good.replace("id: stock", "id: Stock_X").replace(/related: stock/g, "related: Stock_X"), "is not kebab-case");
gate("loop", good.replace("id: print-label", "id: print-label\nafter: hand-over"), "after chain loops");
gate("second-title", good + "\n# Another\n", "second level-1 heading");
gate("plain-words", good.replace("packed, labelled", "packed, labelled (see shop/label.py)"), "a path or file name");
gate("self-related", good.replace("related: stock\nvalue: Stops", "related: check-stock\nvalue: Stops"), 'related names its own id "check-stock"');

// ---- inside git
const { dir, g } = repo("gen repo");
const sp = path.join(dir, "my sdd.md");
fs.writeFileSync(sp, good);
r = gen(sp, path.join(tmp, "untracked.html"));
t("generator: a git repo but an untracked SDD gets no sddCommit", r.code === 0 && /no sddCommit/.test(r.out) && readT(read(path.join(tmp, "untracked.html"))).sddCommit === undefined, r.out.trim());
g("add", "."); g("commit", "-q", "-m", "first");
const c1 = g("rev-parse", "HEAD");
const mapg = path.join(tmp, "mapg.html");
r = gen(sp, mapg);
const T2 = readT(read(mapg));
t("generator: records sdd + sddCommit of a tracked, clean SDD (path with spaces)", r.code === 0 && T2.sddCommit === c1 && T2.sdd[0] === "my sdd.md", `sddCommit ${T2.sddCommit}`);
fs.writeFileSync(sp, good + "\n## Extra\nid: extra\nfeature: Something new.\n");
r = gen(sp, path.join(tmp, "mapd.html"));
t("generator: refuses an SDD with uncommitted changes", r.code === 1 && r.out.startsWith("my sdd.md has uncommitted changes"), r.out.split("\n")[0]);
const mapy = path.join(tmp, "mapy.html");
r = gen(sp, mapy, "--dirty");
t("generator --dirty: draws it with sddCommit \"uncommitted\"", r.code === 0 && readT(read(mapy)).sddCommit === "uncommitted" && find(readT(read(mapy)), "extra") !== undefined, r.out.trim());
const mapc = path.join(tmp, "mapc.html");
r = gen(sp, mapc, "--commit", c1);
t("generator --commit: draws the SDD as it was at that commit", r.code === 0 && readT(read(mapc)).sddCommit === c1 && find(readT(read(mapc)), "extra") === undefined, r.out.trim());
r = gen(sp, path.join(tmp, "mapbad.html"), "--commit", "deadbeef");
t("generator --commit: an unknown commit fails", r.code === 1 && /^cannot read my sdd.md at deadbeef/.test(r.out), r.out.split("\n")[0]);
