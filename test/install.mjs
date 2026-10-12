// "Someone else's website": the package files are served from one origin, the page from another, with no CORS headers.
// Checks every way of using it: one script tag with no config, data attributes, create() by hand (no double spider),
// what is downloaded and when (a desktop preloads two sheets, a phone nothing), a strict Content-Security-Policy, and the ES module build.
//   node build.mjs && node test/install.mjs
import http from "node:http";
import { readFileSync, existsSync, statSync } from "node:fs";
import { resolve, extname, join } from "node:path";
import { launch } from "./_pw.mjs";

const ROOT = resolve(".");
const MIME = { ".js": "text/javascript", ".mjs": "text/javascript", ".cjs": "text/javascript", ".json": "application/json", ".webp": "image/webp", ".html": "text/html" };
const log = [];                                    // every request the package server gets
const serve = (handler) => new Promise((res) => { const s = http.createServer(handler); s.listen(0, "127.0.0.1", () => res(s)); });

const pkgServer = await serve((req, rsp) => {
  const path = decodeURIComponent(req.url.split("?")[0]);
  log.push(path);
  const f = join(ROOT, path);
  if (!f.startsWith(ROOT) || !existsSync(f) || !statSync(f).isFile()) { rsp.writeHead(404); return rsp.end(); }
  // no CORS header, like a plain static host; except for modules, which browsers will not load without one (every real CDN sends it)
  const h = { "content-type": MIME[extname(f)] || "application/octet-stream" };
  if (extname(f) === ".mjs") h["access-control-allow-origin"] = "*";
  rsp.writeHead(200, h);
  rsp.end(readFileSync(f));
});
const PKG = `http://127.0.0.1:${pkgServer.address().port}`;

const pages = {
  "/oneline.html": `<!doctype html><title>one line</title><h1>Somebody else's page</h1><script src="${PKG}/spider-cursor.min.js"></script>`,
  "/deep/er/path/nested.html": `<!doctype html><title>nested</title><h1>Nested route</h1><script src="${PKG}/spider-cursor.js"></script>`,
  "/data.html": `<!doctype html><title>data</title><h1>data attributes</h1><script src="${PKG}/spider-cursor.js" data-size="64" data-perch="false"></script>`,
  "/manual.html": `<!doctype html><title>manual</title><h1>by hand</h1><script src="${PKG}/spider-cursor.js"></script><script>window.s = SpiderCursor.create({ size: 40 });</script>`,
  "/optout.html": `<!doctype html><title>optout</title><h1>data-manual</h1><script src="${PKG}/spider-cursor.js" data-manual></script>`,
  "/narrow.html": `<!doctype html><title>narrow</title><h1>minWidth</h1><script src="${PKG}/spider-cursor.js" data-min-width="5000"></script>`,
  "/esm.html": `<!doctype html><title>esm</title><h1>module</h1><script type="module">import SC from "${PKG}/spider-cursor.mjs"; window.version = SC.version; window.s = SC.create({ src: "${PKG}/assets/", size: 36 });</script>`,
};
const siteServer = await serve((req, rsp) => {
  const body = pages[req.url.split("?")[0]];
  if (req.url === "/favicon.ico") { rsp.writeHead(204); return rsp.end(); }
  if (!body) { rsp.writeHead(404); return rsp.end(); }
  const headers = { "content-type": "text/html" };
  if (req.url.startsWith("/csp")) headers["content-security-policy"] = `default-src 'self'; script-src ${PKG} 'unsafe-inline'; img-src ${PKG} data:; style-src 'self'; connect-src ${PKG}`;
  rsp.writeHead(200, headers); rsp.end(body);
});
pages["/csp.html"] = pages["/oneline.html"];
const SITE = `http://127.0.0.1:${siteServer.address().port}`;

const b = await launch();
const fails = [];
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) fails.push(msg); };
const canvases = (p) => p.evaluate(() => [...document.querySelectorAll("canvas")].map((c) => ({ w: parseFloat(c.style.width), cursorNone: false })));
const open = async (path, vp = { width: 900, height: 600 }) => {
  const p = await b.newPage({ viewport: vp, deviceScaleFactor: 2 });
  p.problems = [];
  p.on("console", (m) => { if (m.type() === "error" || m.type() === "warning") p.problems.push(m.text().slice(0, 160)); });
  p.on("pageerror", (e) => p.problems.push("pageerror " + e.message));
  await p.goto(SITE + path);
  return p;
};
const settle = async (p, ms = 15000) => { const t0 = Date.now(); while (Date.now() - t0 < ms) { await p.waitForTimeout(250); if (await p.evaluate(() => document.documentElement.hasAttribute("data-spider-perched"))) return true; } return false; };

// 1. one line, no config, other origin
{
  log.length = 0;
  const p = await open("/oneline.html");
  await p.waitForTimeout(1500);
  const early = log.filter((x) => x.startsWith("/assets/") && x.endsWith(".webp")).map((x) => x.split("/").pop()).sort();
  check(early.join() === "idle_calm.webp,walk0.webp", "a desktop browser preloads just the two sheets it needs while the page is idle, before any mouse move (" + early.join(", ") + ")");
  await p.mouse.move(600, 400);
  const arrived = await settle(p);
  check(arrived, "one <script> tag, no config, from another origin: the spider finds its sprites, walks in and settles");
  await p.waitForTimeout(500);
  const sheets = log.filter((x) => x.startsWith("/assets/") && x.endsWith(".webp"));
  check(sheets.length === 10, "the other eight sheets (curves, pivot, fidgets) load once the spider has appeared (" + sheets.length + " in all)");
  const tiers = new Set(sheets.map((x) => x.split("/")[2]));
  check(tiers.size === 1, "only one size of sprite is downloaded (tier " + [...tiers].join(",") + ", " + sheets.length + " sheets)");
  check(!log.some((x) => x.endsWith("manifest.json")), "no manifest.json request (so no CORS error from a plain static host)");
  check(p.problems.length === 0, "no console errors or warnings" + (p.problems.length ? ": " + p.problems.join(" | ") : ""));
  check((await canvases(p)).length === 1, "exactly one spider");
  await p.close();
}
// 1b. a phone: no mouse, so nothing is downloaded at all, not even after a tap
{
  log.length = 0;
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  await p.goto(SITE + "/oneline.html");
  await p.waitForTimeout(2000);
  await p.touchscreen.tap(200, 400);
  await p.waitForTimeout(1500);
  const got = log.filter((x) => x.startsWith("/assets/"));
  const script = log.filter((x) => x.endsWith("spider-cursor.min.js")).length;
  check(script === 1 && got.length === 0, "on a phone only the 14 KB script is fetched: no sprites, even after a tap (" + got.length + " sprite requests)");
  check((await p.evaluate(() => document.querySelectorAll("canvas").length)) <= 1, "and no spider is drawn");
  await ctx.close();
}
// 2. nested route
{
  const p = await open("/deep/er/path/nested.html");
  await p.mouse.move(500, 300);
  check(await settle(p), "works from a nested page path (assets are found relative to the script, not the page)");
  await p.close();
}
// 3. data attributes
{
  const p = await open("/data.html");
  await p.mouse.move(500, 300);
  await p.waitForTimeout(1500);
  const w = (await canvases(p))[0]?.w;
  check(w > 150, "data-size is honoured (frame " + w + " px for a 64 px spider)");
  await p.waitForTimeout(12000);
  check(!(await p.evaluate(() => document.documentElement.hasAttribute("data-spider-perched"))), "data-perch=\"false\" keeps the arrow");
  await p.close();
}
// 4. create() by hand does not start a second spider; data-manual starts none
{
  const p = await open("/manual.html");
  await p.mouse.move(500, 300);
  await p.waitForTimeout(1500);
  check((await canvases(p)).length === 1, "a hand-made create() after the tag does not double up");
  await p.close();
  const q = await open("/optout.html");
  await q.waitForTimeout(800);
  check((await canvases(q)).length === 0, "data-manual: nothing starts by itself");
  await q.close();
}
// 5. minWidth
{
  const p = await open("/narrow.html");
  await p.mouse.move(500, 300);
  await p.waitForTimeout(800);
  check((await canvases(p)).length === 0, "data-min-width hides it on a narrower window");
  await p.close();
}
// 6. strict CSP: no inline styles allowed
{
  const p = await open("/csp.html");
  await p.mouse.move(600, 400);
  const arrived = await settle(p);
  const cursor = await p.evaluate(() => getComputedStyle(document.body).cursor);
  check(arrived && cursor === "none", "under a strict Content-Security-Policy the arrow is still hidden when it settles (cursor: " + cursor + ")");
  check(p.problems.length === 0, "and the policy reports no violations" + (p.problems.length ? ": " + p.problems.join(" | ") : ""));
  await p.close();
}
// 7. ES module
{
  const p = await open("/esm.html");
  await p.mouse.move(500, 300);
  await p.waitForTimeout(1200);
  const v = await p.evaluate(() => window.version);
  check(/^\d+\.\d+\.\d+$/.test(v) && (await canvases(p)).length === 1, "import from the .mjs build works and is stamped with its version (" + v + ")");
  await p.close();
}
await b.close();
pkgServer.close(); siteServer.close();
if (fails.length) { console.log("\n" + fails.length + " check(s) failed"); process.exit(1); }
console.log("\nall install checks passed");
