// Sibling order: a loop in `after` (the validator rejects it, but ordered() must not depend on that) must end, not hang.
// It runs in a child process with a timeout, so removing the `placed` guard in sdd-order.js fails the test instead of hanging it.
const { spawnSync } = require("child_process");
const path = require("path");
const { t } = require("./test-helpers");
const code = `const { ordered } = require(${JSON.stringify(path.join(__dirname, "sdd-order.js"))});
const k = (id, after) => ({ fields: { id, after } });
console.log(ordered([k("a", "c"), k("b", "a"), k("c", "b"), k("d")]).map(x => x.fields.id).join(","));`;
const r = spawnSync("node", ["-e", code], { encoding: "utf8", timeout: 5000 });
t("ordered: an after loop ends and keeps every box once", r.status === 0 && r.stdout.trim() === "d,a,b,c", r.error ? "timed out (hang)" : r.stdout + r.stderr);
