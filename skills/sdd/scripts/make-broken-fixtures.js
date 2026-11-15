// Regenerates the four broken fixtures from fixtures/good.md (one deliberate defect each). Run when good.md changes.
const fs = require("fs"), path = require("path");
const d = path.join(__dirname, "fixtures");
const g = fs.readFileSync(path.join(d, "good.md"), "utf8");
const swap = (t, a, b) => { if (!t.includes(a)) throw new Error("fixture text not found: " + a); return t.replace(a, b); };
const w = (n, t) => fs.writeFileSync(path.join(d, n), t);
w("broken-no-feature.md", swap(g, "feature: Before paying, every product in the basket is compared with what the shop really has.\n", ""));
w("broken-duplicate-id.md", swap(g, "id: print-label", "id: check-stock"));
w("broken-dangling.md", swap(swap(g, "related: stock\nvalue: Gets the goods", "related: ghost-feature\nvalue: Gets the goods"), "after: print-label", "after: label-step"));
w("broken-top-level-detail.md", swap(g, "feature: The order is picked from the shelf, packed, labelled and handed to the carrier.", "feature: The order is picked, packed and handed to the carrier by label.py within 2 days."));
console.log("wrote 4 broken fixtures");
