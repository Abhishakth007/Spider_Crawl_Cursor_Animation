// What is the main thread doing during the long frames?   node test/trace.mjs [runtime=spider-cursor.js] [dsf=2] [size=34]
// Records a Chrome trace of a walk that uses every gait strip, finds main-thread tasks longer than 9 ms, and prints what ran inside them.
import http from "node:http";
import { readFileSync, existsSync, statSync } from "node:fs";
import { resolve, extname, join } from "node:path";
import { launch } from "./_pw.mjs";

const runtime = process.argv[2] || "spider-cursor.js", dsf = Number(process.argv[3] || 2), size = Number(process.argv[4] || 34);
const ROOT = resolve("."), MIME = { ".js": "text/javascript", ".json": "application/json", ".webp": "image/webp", ".html": "text/html" };
const server = http.createServer((req, rsp) => {
  const path = decodeURIComponent(req.url.split("?")[0]);
  if (path === "/t.html") {
    rsp.writeHead(200, { "content-type": "text/html" });
    return rsp.end(`<!doctype html><body style="margin:0;background:#f4f1ea;height:100vh"><script src="/${runtime}" data-manual></script>
<script>window.sp = SpiderCursor.create(Object.assign({ src: "/assets/", size: ${size}, quality: "full", fidget: false }, ${process.env.SPIDER_OPTS || "{}"}));</script>`);
  }
  const f = join(ROOT, path);
  if (!f.startsWith(ROOT) || !existsSync(f) || !statSync(f).isFile()) { rsp.writeHead(404); return rsp.end(); }
  rsp.writeHead(200, { "content-type": MIME[extname(f)] || "application/octet-stream", "cache-control": "no-store" });
  rsp.end(readFileSync(f));
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const browser = await launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: dsf });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
await page.goto(`http://127.0.0.1:${server.address().port}/t.html`);
await sleep(1500);
await page.mouse.move(640, 400);
await page.waitForFunction(() => window.sp && window.sp.state().ready, null, { timeout: 15000 });
await sleep(14000);                                              // appear, prefetch every sheet, settle

await browser.startTracing(page, { categories: ["devtools.timeline", "disabled-by-default-devtools.timeline", "toplevel", "blink", "cc", "gpu", "v8", "disabled-by-default-devtools.timeline.frame"] });
const path = (t) => {
  if (t < 4) { const a = t * 0.9; return [640 + 300 * Math.cos(a), 400 + 200 * Math.sin(a)]; }
  if (t < 8) { const k = (t - 4) / 4; return [140 + 1000 * k, 400 + 260 * Math.sin(k * 20)]; }
  return [1140, 400];
};
const t0 = Date.now();
while ((Date.now() - t0) / 1000 < 9) { const [x, y] = path((Date.now() - t0) / 1000); await page.mouse.move(x, y); await sleep(14); }
const buf = await browser.stopTracing();
const ev = JSON.parse(buf.toString()).traceEvents;
const names = new Map(ev.filter((e) => e.ph === "M" && e.name === "thread_name").map((e) => [e.pid + ":" + e.tid, e.args.name]));
const pidOf = ev.find((e) => e.ph === "M" && e.name === "process_name" && e.args.name === "Renderer");
const mains = ev.filter((e) => e.ph === "M" && e.name === "thread_name" && e.args.name === "CrRendererMain");
const main = mains.map((e) => e.pid + ":" + e.tid);
const onMain = ev.filter((e) => e.ph === "X" && main.includes(e.pid + ":" + e.tid) && e.dur);
const tasks = onMain.filter((e) => e.name === "RunTask" && e.dur > 9000).sort((a, b) => b.dur - a.dur).slice(0, 8);
console.log("main-thread tasks over 9 ms:", onMain.filter((e) => e.name === "RunTask" && e.dur > 9000).length, "of", onMain.filter((e) => e.name === "RunTask").length);
for (const k of tasks) {
  const inside = onMain.filter((e) => e !== k && e.ts >= k.ts && e.ts + e.dur <= k.ts + k.dur && e.dur > 400)
    .sort((a, b) => b.dur - a.dur).slice(0, 6).map((e) => `${e.name} ${(e.dur / 1000).toFixed(1)}ms`);
  console.log(`${(k.dur / 1000).toFixed(1)} ms @${((k.ts - tasks[0].ts) / 1000).toFixed(0)}  ->`, inside.join(" | "));
}
// and the other threads busy at the same moments (raster, GPU, compositor)
const busy = new Map();
for (const e of ev.filter((e) => e.ph === "X" && e.dur > 3000)) { const n = names.get(e.pid + ":" + e.tid) || "?"; if (n === "CrRendererMain") continue; const key = n + " / " + e.name; busy.set(key, (busy.get(key) || 0) + 1); }
console.log("other threads with events over 3 ms:", [...busy.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8).map(([k, v]) => k + " x" + v).join(" | "));
await browser.close();
server.close();
