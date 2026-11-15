// Writes a map page for sdd-to-map.js: the data T, and the page texts that come from the SDD (title, h1, intro, footer).
// Every marker it replaces must be found; a missing one throws (nothing is silently left stale).
const { bounds, serialize, UNCOMMITTED } = require("../../system-map/scripts/map-data");

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function sub(html, re, text, label) {
  if (!re.test(html)) throw new Error(`marker not found in the page: ${label}`);
  return html.replace(re, typeof text === "function" ? text : () => text);
}

// html: the existing map or the template; isNew: html is the template (its lane titles are set too)
function writePage(html, T, sddCommit, isNew) {
  const { a, b } = bounds(html);
  let head = html.slice(0, a), rest = html.slice(b);
  const short = sddCommit && sddCommit !== UNCOMMITTED ? sddCommit.slice(0, 7) : null;
  const intro = `${esc(T.desc || "")} Click any box to see how it works inside. Drawn from the SDD${short ? " at commit " + short : ""}.`;
  head = sub(head, /<title>[\s\S]*?<\/title>/, `<title>${esc(T.name)} Map</title>`, "<title>");
  head = sub(head, /<h1>[\s\S]*?<\/h1>/, `<h1>${esc(T.name)} Map</h1>`, "<h1>");
  head = sub(head, /(<header>[\s\S]*?<\/h1>\s*)<p>[\s\S]*?<\/p>/, (m, p1) => p1 + "<p>" + intro + "</p>", "<p> after the <h1>");
  head = sub(head, /<footer>[\s\S]*?<\/footer>/, "<footer>Drawn from the SDD by sdd-to-map.js. Items marked in red are open questions, not facts.</footer>", "<footer>");
  if (isNew) {
    // the template marks each lane title as /*lane:<name>*/"<its text>"; the text itself is not repeated here
    rest = sub(rest, /\/\*lane:flow\*\/"[^"]*"/, '"The flow · in order"', "flow lane title");
    rest = sub(rest, /\/\*lane:support\*\/"[^"]*"/, '"Shared parts · used by the flow"', "support lane title");
  }
  return head + "const T=" + serialize(T) + ";\n\n" + rest;
}

module.exports = { writePage, esc };
