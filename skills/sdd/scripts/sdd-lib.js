// Entry point of the SDD tools' shared code (skills/sdd/SKILL.md): parser, validator, git helpers.
module.exports = { ...require("./sdd-parse"), ...require("./sdd-check"), ...require("./sdd-git") };
