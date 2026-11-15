// Shared by the map tools: where the data T sits in a map page, how to read it, how to write it safely.
// The page is: ... <script> ... const T={...}; <MARK> ...rendering code... </script>
const MARK = "/* ───────── index";

function bounds(html) {
  const s = html.indexOf("<script");
  const a = s < 0 ? -1 : html.indexOf("const T=", s);
  const b = html.lastIndexOf(MARK);  // last: a text inside the data may quote the marker, the rendering code has it once
  if (a < 0 || b < a) throw new Error(`the page has no <script> with "const T=" followed by "${MARK}"`);
  return { a, b };
}

function readT(html) {
  const { a, b } = bounds(html);
  return new Function(html.slice(a, b) + ";return T;")();
}

// JSON for the <script>: < > & become \uXXXX so no text can close the script or open a comment
function serialize(T) {
  return JSON.stringify(T, null, 1).replace(/</g, "\\u003c").replace(/>/g, "\\u003e").replace(/&/g, "\\u0026");
}

// problems that make the page itself broken (not the data): text in the data that ends the script, or extra </script>
function pageProblems(html) {
  const { a, b } = bounds(html);
  const out = [];
  if (/<\/script|<!--/i.test(html.slice(a, b))) out.push("the data holds </script or <!-- (an unescaped < ends the script early)");
  const n = (html.slice(b).match(/<\/script>/gi) || []).length;
  if (n !== 1) out.push(`expected exactly one </script> after the data, found ${n}`);
  return out;
}

module.exports = { MARK, bounds, readT, serialize, pageProblems };
