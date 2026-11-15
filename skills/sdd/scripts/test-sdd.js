// Tests of the SDD tools. Usage: node test-sdd.js   (exit 1 if any test fails)
// test-parser.js: the parser's edge cases. test-validate.js: the validator (fixtures, each rule, --since).
// test-generate.js: the map generator (git, determinism, diff). test-page.js: the map page (escaping, markers, readT).
require("./test-parser");
require("./test-validate");
require("./test-generate");
require("./test-page");
require("./test-helpers").summary();
