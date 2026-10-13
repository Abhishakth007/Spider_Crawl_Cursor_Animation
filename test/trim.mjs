// A spider that has been sitting on the pointer gives back the memory of its turning sheets, and gets them again when it moves.
//   node build.mjs && node test/trim.mjs
import http from "node:http";
import { readFileSync, existsSync, statSync } from "node:fs";
import { resolve, extname, join } from "node:path";
import { launch } from "./_pw.mjs";

const ROOT = resolve("."), MIME = { ".js": "text/javascript", ".json": "application/json", ".webp": "image/webp", ".html": "text/html" };
const requests = [];
const server = http.createServer((req, rsp) => {
  const path = decodeURIComponent(req.url.split("?")[0]);
  if (path === "/t.html") {
    rsp.writeHead(200, { "content-type": "text/html" });
    return rsp.end(`<!doctype html><body style="margin:0;height:100vh"><script src="/spider-cursor.js" data-manual></script>
<script>window.sp = SpiderCursor.create({ src: "/assets/", size: 34, quality: "full", fidget: false, idleTrim: 2500 });</script>`);
  }
  if (path === "/favicon.ico") { rsp.writeHead(204); return rsp.end(); }
  const f = join(ROOT, path);
  if (!f.startsWith(ROOT) || !existsSync(f) || !statSync(f).isFile()) { rsp.writeHead(404); return rsp.end(); }
  if (/\.webp$/.test(f)) requests.push(path.split("/").slice(-2).join("/"));
  rsp.writeHead(200, { "content-type": MIME[extname(f)] || "application/octet-stream", "cache-control": "no-store" });
  rsp.end(readFileSync(f));
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const browser = await launch();
const page = await browser.newPage({ viewport: { width: 1000, height: 640 }, deviceScaleFactor: 2 });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => { if (m.type() === "error" || m.type() === "warning") errors.push(m.text()); });
await page.goto(`http://127.0.0.1:${server.address().port}/t.html`);
const fail = [];
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) fail.push(msg); };
const state = () => page.evaluate(() => window.sp.state());

await page.mouse.move(500, 300);
await page.waitForFunction(() => window.sp && window.sp.state().ready, null, { timeout: 15000 });
for (const [x, y] of [[800, 200], [200, 500], [700, 520]]) { await page.mouse.move(x, y, { steps: 25 }); await sleep(900); }   // curves, so the turning sheets are wanted
await page.waitForFunction(() => window.sp.state().perched, null, { timeout: 40000 });
const busy = await state();
check(busy.cache.readyBytes > 15e6, `after walking, the decoded sheets are resident (${(busy.cache.readyBytes / 1048576).toFixed(1)} MB)`);
await sleep(4000);                                                                  // longer than idleTrim
const quiet = await state();
check(quiet.cache.readyBytes < busy.cache.readyBytes * 0.4, `after sitting still, the turning sheets are given back (${(quiet.cache.readyBytes / 1048576).toFixed(1)} MB left)`);
check(quiet.perched && quiet.mode === "idle", "it is still perched and idle");
const before = requests.length;
await page.mouse.move(150, 120, { steps: 30 });                                     // off again, across the page
await sleep(6000);
const after = await state();
check(after.error === null && errors.length === 0, `no error after walking again ${JSON.stringify(errors.slice(0, 2))}`);
check(after.mode !== "idle" || !after.perched, "it set off again");
check(requests.length - before <= 6, `the sheets it needed again came back (${requests.length - before} requests)`);
const drawn = await page.evaluate(() => { const c = document.querySelector("canvas"); const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 20) n++; return n; });
check(drawn > 500, `and it is drawn (${drawn} opaque pixels)`);
await browser.close();
server.close();
if (fail.length) { console.log("\nFAILED:\n - " + fail.join("\n - ")); process.exit(1); }
console.log("\nall trim checks pass");
