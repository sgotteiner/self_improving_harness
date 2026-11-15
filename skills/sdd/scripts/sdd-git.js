// git helpers for the SDD tools: `file` is the absolute path of the SDD file.
const { execFileSync } = require("child_process");
const path = require("path");

// raw: keep the output as is (file text); otherwise it is trimmed
function git(file, args, raw) {
  const out = execFileSync("git", ["-C", path.dirname(file), ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  return raw ? out : out.trim();
}
function show(file, commit) {
  return git(file, ["show", `${commit}:${git(file, ["rev-parse", "--show-prefix"])}${path.basename(file)}`], true);
}
function repoPath(file) {
  try { return git(file, ["rev-parse", "--show-prefix"]) + path.basename(file); } catch (e) { return null; }
}

module.exports = { git, show, repoPath };
