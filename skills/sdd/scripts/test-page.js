// Map page tests: HTML escaping, refreshed page texts, missing markers, check-structure on a broken page, readT.
const { fs, path, fx, gen, check, tmp, good, write, read, t, repo } = require("./test-helpers");
const { readT, MARK, pageProblems } = require("../../system-map/scripts/map-data");
const find = (n, id) => n.id === id ? n : (n.children || []).map(c => find(c, id)).find(Boolean);
const hostile = '</script><script>alert(1)</script> <!-- & "q"';
const evil = good.replace("# Order Desk\nfeature: A small shop system that takes customer orders and gets them packed and sent.",
  `# Order </title><b>Desk</b> & Co\nfeature: A shop <script>x</script> & "more".`)
  .replace("feature: When the bank says no, the customer may try again before the order is dropped.", `feature: Retry ${hostile}`);
t("page: the evil SDD is still valid", evil !== good && evil.includes("</script><script>"));
const mapE = path.join(tmp, "evil.html");
let r = gen(write("evil.md", evil), mapE);
const html = read(mapE);
t("page: generation succeeds", r.code === 0, r.out.trim());
t("page: no </script> or <!-- inside the data", pageProblems(html).length === 0, pageProblems(html).join());
t("page: exactly one </script> in the whole page", html.match(/<\/script>/gi).length === 1);
t("page: the data decodes back to the exact text", find(readT(html), "retry-payment").desc === `Retry ${hostile}` && readT(html).name === "Order </title><b>Desk</b> & Co", JSON.stringify(readT(html).name));
t("page: the < > & are \\u-escaped in the JSON", /\\u003c\/script\\u003e\\u003cscript\\u003e/.test(html) && html.includes("\\u0026"));
const head = html.slice(0, html.indexOf("<script>"));
t("page: title, h1, intro are HTML-escaped", head.includes("<title>Order &lt;/title&gt;&lt;b&gt;Desk&lt;/b&gt; &amp; Co Map</title>") && head.includes("<h1>Order &lt;/title&gt;&lt;b&gt;Desk&lt;/b&gt; &amp; Co Map</h1>") && head.includes('<p>A shop &lt;script&gt;x&lt;/script&gt; &amp; "more". Click any box'), head.match(/<p>.*<\/p>/)[0]);
t("page: check-structure passes the evil page", check(mapE).out.trim() === "structure ok; 9 nodes", check(mapE).out.trim());

// ---- check-structure detects a broken page
const broken = path.join(tmp, "broken.html");
fs.writeFileSync(broken, html.replace('"name": "Take the order"', '"name": "</script>x"'.replace("</script>", "</script>")));
r = check(broken);
t("check-structure: a </script> in the data is reported", r.code === 1 && r.out.trim() === "the data holds </script or <!-- (an unescaped < ends the script early)", r.out.trim());
fs.writeFileSync(broken, html.replace(/<\/script>/, "</script></script>"));
t("check-structure: two </script> after the data is reported", check(broken).out.includes("expected exactly one </script> after the data, found 2"), check(broken).out.trim());
fs.writeFileSync(broken, html.replace(MARK, "/* gone"));
r = check(broken);
t("check-structure: a missing marker is reported", r.code === 1 && r.out.startsWith("cannot read the map: the page has no <script>"), r.out.trim());
t("readT: a text in the data that quotes the marker still reads", readT(html.replace('"Take the order"', JSON.stringify(MARK))).children[0].name === MARK);
t("readT: a title that says const T= does not confuse it", readT(html.replace("<title>", "<title>const T=")).name === "Order </title><b>Desk</b> & Co");

// ---- regenerating an existing map refreshes title, h1, intro (with the commit) and footer
const { dir, g } = repo("regen");
const sp = path.join(dir, "sdd.md");
fs.writeFileSync(sp, good); g("add", "."); g("commit", "-q", "-m", "first");
const mapR = path.join(tmp, "regen.html");
gen(sp, mapR);
fs.writeFileSync(mapR, read(mapR).replace("<footer>", "<footer>STALE ").replace(/<p>[\s\S]*?<\/p>/, "<p>STALE</p>").replace("<title>", "<title>STALE "));
const next = good.replace("# Order Desk\nfeature: A small shop system that takes customer orders and gets them packed and sent.", "# Shop Desk\nfeature: A renamed shop system.");
fs.writeFileSync(sp, next); g("commit", "-qam", "second");
const c2 = g("rev-parse", "HEAD");
r = gen(sp, mapR);
const h2 = read(mapR);
t("regenerate: title, h1, intro with the commit, footer refreshed on an existing map", r.code === 0 && h2.includes("<title>Shop Desk Map</title>") && h2.includes("<h1>Shop Desk Map</h1>") && h2.includes(`<p>A renamed shop system. Click any box to see how it works inside. Drawn from the SDD at commit ${c2.slice(0, 7)}.</p>`) && h2.includes("<footer>Drawn from the SDD by sdd-to-map.js.") && !h2.includes("STALE"), r.out.trim());
// ---- a missing template marker fails loudly and writes nothing
for (const [label, edit] of [["<footer>", (s) => s.replace("<footer>", "<div>")], ["<h1>", (s) => s.replace("<h1>", "<h2>")], ["lane title", (s) => s.replace("The pipeline · news to video", "x")], ["data marker", (s) => s.replace(MARK, "/* x")]]) {
  const tpl = write("tpl.html", edit(read(path.join(__dirname, "..", "..", "system-map", "assets", "template.html"))));
  const out = path.join(tmp, "tpl-out.html");
  r = gen(write("g2.md", good), out, "--template", tpl);
  t(`generator: template without ${label} fails loudly, writes nothing`, r.code === 1 && /marker not found|has no <script>/.test(r.out) && !fs.existsSync(out), r.out.trim().slice(0, 120));
}
