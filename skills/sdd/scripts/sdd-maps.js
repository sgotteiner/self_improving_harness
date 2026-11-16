// Finds the maps drawn from an SDD: the tracked .html files of its repo whose data T lists the SDD file in `sdd`.
// Library: maps(repoRoot) -> [{ rel, file, sdd: [repo-relative paths], sddCommit }]. Used by sdd-hook.js.
// CLI: node sdd-maps.js <sdd.md>  prints JSON [{ map, sddCommit, last, current }]: `last` = the SDD's last commit,
//   `current` = the map was drawn from it. [] when the SDD has no map, null when it is not in a git repo. Used by the project check (scripts/recall/projcheck.py).
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { readT } = require("../../system-map/scripts/map-data");
const { git, repoPath } = require("./sdd-git");

function maps(repo) {
  const out = [];
  const names = execFileSync("git", ["-C", repo, "ls-files", "-z", "--", "*.html"], { encoding: "utf8" }).split("\0").filter(Boolean);
  for (const rel of names) {
    const file = path.join(repo, rel);
    try {
      const text = fs.readFileSync(file, "utf8");
      if (!text.includes("const T=")) continue;
      const T = readT(text);
      if (Array.isArray(T.sdd)) out.push({ rel, file, sdd: T.sdd, sddCommit: T.sddCommit || null });
    } catch (e) { /* not a map of ours */ }
  }
  return out;
}

if (require.main === module) {
  const sdd = path.resolve(process.argv[2] || "");
  const rp = repoPath(sdd);
  if (!process.argv[2] || rp === null) { console.log("null"); process.exit(0); }  // not in a git repo: no map and no hooks to speak of
  const repo = git(sdd, ["rev-parse", "--show-toplevel"]);
  let last = "";
  try { last = git(sdd, ["log", "-1", "--format=%H", "--", path.basename(sdd)]); } catch (e) { /* no commits */ }
  console.log(JSON.stringify(maps(repo).filter(m => m.sdd.includes(rp)).map(m => ({ map: m.file, sddCommit: m.sddCommit, last, current: !!last && m.sddCommit === last }))));
}

module.exports = { maps };
