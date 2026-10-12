// The published package, the way a stranger uses it: a page on some other origin loads the one-liner from jsDelivr.
// Needs the network and a published version.   node test/cdn.mjs [version]
import http from "node:http";
import { readFileSync } from "node:fs";
import { launch } from "./_pw.mjs";

const version = process.argv[2] || JSON.parse(readFileSync("package.json", "utf8")).version;
const CDN = "https://cdn.jsdelivr.net/npm/spider-crawl-cursor";
const urls = {
  "pinned file": `${CDN}@${version}/spider-cursor.min.js`,
  "major version (what the README shows)": `${CDN}@${version.split(".")[0]}/spider-cursor.min.js`,
  "bare package name": CDN,
  "readable build": `${CDN}@${version}/spider-cursor.js`,
};
const page = (src) => `<!doctype html><title>cdn</title><h1>A stranger's page</h1><script src="${src}"></script>`;
let current = "";
const server = http.createServer((req, rsp) => {
  if (req.url === "/favicon.ico") { rsp.writeHead(204); return rsp.end(); }
  rsp.writeHead(200, { "content-type": "text/html" }); rsp.end(page(current));
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const SITE = `http://127.0.0.1:${server.address().port}/`;

const b = await launch();
const fails = [];
for (const [name, url] of Object.entries(urls)) {
  current = url;
  const p = await b.newPage({ viewport: { width: 900, height: 600 }, deviceScaleFactor: 2 });
  const problems = [], reqs = [];
  p.on("console", (m) => { if (m.type() === "error" || m.type() === "warning") problems.push(m.text().slice(0, 140)); });
  p.on("request", (r) => { if (r.url().includes("/assets/")) reqs.push(r.url()); });
  await p.goto(SITE);
  await p.mouse.move(600, 400);
  let ok = false; const t0 = Date.now();
  while (Date.now() - t0 < 25000 && !ok) { await p.waitForTimeout(300); ok = await p.evaluate(() => document.documentElement.hasAttribute("data-spider-perched")); }
  const tier = reqs.length ? reqs[0].match(/assets\/(\d+)\//)?.[1] : "-";
  console.log((ok && !problems.length ? "ok   " : "FAIL ") + name + "  (settled: " + ok + ", sheets: " + reqs.length + " at tier " + tier + (problems.length ? ", problems: " + problems.join(" | ") : "") + ")");
  if (!ok || problems.length) fails.push(name);
  await p.close();
}
await b.close(); server.close();
if (fails.length) { console.log("\nfailed: " + fails.join(", ")); process.exit(1); }
console.log("\nthe published package works from the CDN");
