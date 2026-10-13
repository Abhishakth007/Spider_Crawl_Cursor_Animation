// What the spider costs the page, measured in real Chrome with a scripted pointer.
//   node build.mjs && node test/bench.mjs [runtime=spider-cursor.js] [dsf=2] [size=34] [label] [--fidget] [--lite]
//
// Phases: load (bytes and requests before any pointer), idle (is the page really left alone?), a 14 s walk (circle, zig-zag, a dash
// to the far corner and back, a rest) with frame pacing, long tasks and main-thread time per second, then a rest and a fidget check.
import http from "node:http";
import { readFileSync, existsSync, statSync } from "node:fs";
import { resolve, extname, join } from "node:path";
import { launch } from "./_pw.mjs";

const args = process.argv.slice(2).filter((a) => !a.startsWith("--"));
const flag = (n) => process.argv.includes("--" + n);
const runtime = args[0] || "spider-cursor.js";
const dsf = Number(args[1] || 2), size = Number(args[2] || 34), label = args[3] || runtime;
const ROOT = resolve(".");
const MIME = { ".js": "text/javascript", ".json": "application/json", ".webp": "image/webp", ".html": "text/html" };

const served = [];
const server = http.createServer((req, rsp) => {
  const path = decodeURIComponent(req.url.split("?")[0]);
  if (path === "/bench.html") {
    rsp.writeHead(200, { "content-type": "text/html" });
    return rsp.end(`<!doctype html><body style="margin:0;background:#f4f1ea;height:100vh"><script src="/${runtime}" data-manual></script>
<script>window.sp = SpiderCursor.create(Object.assign({ src: "/assets/", size: ${size}, quality: "${flag("lite") ? "lite" : "full"}", fidget: ${flag("fidget")} }, ${process.env.SPIDER_OPTS || "{}"}));</script>`);
  }
  const f = join(ROOT, path);
  if (!f.startsWith(ROOT) || !existsSync(f) || !statSync(f).isFile()) { rsp.writeHead(404); return rsp.end(); }
  const body = readFileSync(f);
  served.push({ path, bytes: body.length });
  rsp.writeHead(200, { "content-type": MIME[extname(f)] || "application/octet-stream", "cache-control": "no-store" });
  rsp.end(body);
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));

const browser = await launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: dsf });
const cdp = await page.context().newCDPSession(page);
await cdp.send("Performance.enable");
const metrics = async () => Object.fromEntries((await cdp.send("Performance.getMetrics")).metrics.map((m) => [m.name, m.value]));
const diff = (a, b) => ({ task: b.TaskDuration - a.TaskDuration, script: b.ScriptDuration - a.ScriptDuration, layout: b.LayoutDuration - a.LayoutDuration, style: b.RecalcStyleDuration - a.RecalcStyleDuration, heap: b.JSHeapUsedSize });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const q = (a, p) => a[Math.min(a.length - 1, Math.floor(p * a.length))];
await page.addInitScript(() => {
  window.__long = [];
  try { new PerformanceObserver((l) => l.getEntries().forEach((e) => window.__long.push(Math.round(e.duration)))).observe({ type: "longtask", buffered: true }); } catch {}
  window.__logFrames = (on) => {
    if (!on) { window.__logging = false; return; }
    window.__frames = []; window.__logging = true; let last = performance.now();
    window.__spikes = [];
    const loop = (t) => { if (!window.__logging) return; const d = t - last; window.__frames.push(d); if (d > 12 && window.sp) window.__spikes.push({ at: Math.round(t), ms: Math.round(d), strip: window.sp.state().strip }); last = t; requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
  };
});

// 1. load: what is fetched before anyone touches the mouse
await page.goto(`http://127.0.0.1:${server.address().port}/bench.html`);
await sleep(2500);
const loadBytes = served.filter((s) => /\.webp$/.test(s.path)).reduce((n, s) => n + s.bytes, 0);
const out = { label, dsf, size, quality: flag("lite") ? "lite" : "full", load: { sheets: served.filter((s) => /\.webp$/.test(s.path)).map((s) => s.path.split("/").slice(-2).join("/")), kb: Math.round(loadBytes / 1024) } };

// 2. idle after the first appearance: is it quiet?
await page.mouse.move(640, 400);
await page.waitForFunction(() => window.sp && window.sp.state().ready, null, { timeout: 15000 });
await sleep(9000);                                                // it walks in, settles and is left alone
const st0 = await page.evaluate(() => window.sp.state());
await sleep(4000);
const st1 = await page.evaluate(() => window.sp.state());
out.idle = { perched: st1.perched, mode: st1.mode, rafTicksIn4s: st1.metrics.rafTicks - st0.metrics.rafTicks, drawsIn4s: st1.metrics.draws - st0.metrics.draws };

// 3. the walk
const path = (t) => {
  if (t < 4) { const a = t * 0.9; return [640 + 300 * Math.cos(a), 400 + 200 * Math.sin(a)]; }
  if (t < 8) { const k = (t - 4) / 4; return [140 + 1000 * k, 400 + 260 * Math.sin(k * 20)]; }
  if (t < 9) return [1140, 400];
  if (t < 11) { const k = (t - 9) / 2; return [1140 - 1000 * k, 400 - 300 * k]; }
  if (t < 12.5) { const k = (t - 11) / 1.5; return [140 + 1000 * k, 100 + 600 * k]; }
  return [1140, 700];
};
const profiling = flag("profile");
if (profiling) { await cdp.send("Profiler.enable"); await cdp.send("Profiler.setSamplingInterval", { interval: 100 }); await cdp.send("Profiler.start"); }
await page.evaluate(() => window.__logFrames(true));
const m0 = await metrics();
const w0 = await page.evaluate(() => window.sp.state());
const t0 = Date.now(), cpuNames = [];
let moves = 0;
while ((Date.now() - t0) / 1000 < 14) {
  const [x, y] = path((Date.now() - t0) / 1000);
  await page.mouse.move(x, y); moves++;
  await sleep(14);
}
const m1 = await metrics();
if (profiling) {
  const { profile } = await cdp.send("Profiler.stop");
  const self = new Map(), byId = new Map(profile.nodes.map((n) => [n.id, n]));
  const dts = profile.timeDeltas; let total = 0;
  profile.samples.forEach((id, i) => { const n = byId.get(id), key = (n.callFrame.functionName || "(anon)") + ":" + n.callFrame.lineNumber; self.set(key, (self.get(key) || 0) + dts[i]); total += dts[i]; });
  out.profileTopMs = [...self.entries()].sort((a, b) => b[1] - a[1]).slice(0, 14).map(([k, v]) => k + " " + (v / 1000).toFixed(0) + "ms");
  out.profileTotalMs = Math.round(total / 1000);
}
const frames = await page.evaluate(() => { window.__logFrames(false); return window.__frames.slice(5); });
const w1 = await page.evaluate(() => window.sp.state());
const dt = diff(m0, m1);
const sorted = frames.slice().sort((a, b) => a - b);
const long = await page.evaluate(() => window.__long);
const spikes = await page.evaluate(() => window.__spikes);
out.walk = {
  seconds: 14, pointerMoves: moves,
  frameMs: { p50: +q(sorted, 0.5).toFixed(1), p95: +q(sorted, 0.95).toFixed(1), p99: +q(sorted, 0.99).toFixed(1), max: +sorted[sorted.length - 1].toFixed(1) },
  framesOver20ms: frames.filter((f) => f > 20).length, framesOver33ms: frames.filter((f) => f > 33.4).length, frames: frames.length,
  longTasks: long.length, longTaskMs: long, spikes,
  mainThreadMsPerSec: +(dt.task * 1000 / 14).toFixed(1), styleMsPerSec: +(dt.style * 1000 / 14).toFixed(2), scriptMsPerSec: +(dt.script * 1000 / 14).toFixed(1), layoutMsPerSec: +(dt.layout * 1000 / 14).toFixed(2),
  heapMB: +(dt.heap / 1048576).toFixed(1), draws: w1.metrics.draws - w0.metrics.draws, rafTicks: w1.metrics.rafTicks - w0.metrics.rafTicks,
  tier: w1.tier, cacheMB: +(w1.cache.bytes / 1048576).toFixed(1), error: w1.error,
};
out.afterWalk = { totalSheetKB: Math.round(served.filter((s) => /\.webp$/.test(s.path)).reduce((n, s) => n + s.bytes, 0) / 1024), sheets: served.filter((s) => /\.webp$/.test(s.path)).length, list: served.filter((s) => /\.webp$/.test(s.path)).map((s) => s.path.split('/').slice(-2).join('/')) };

// 4. at rest again: quiet? (first let it finish the long walk to the corner and settle)
const arrive0 = Date.now();
while (Date.now() - arrive0 < 40000 && !(await page.evaluate(() => window.sp.state().perched))) await sleep(250);
out.arrivedAfterMs = Date.now() - arrive0;
await sleep(3000);
const r0 = await page.evaluate(() => window.sp.state());
const mr0 = await metrics();
await sleep(5000);
const r1 = await page.evaluate(() => window.sp.state());
const mr1 = await metrics();
out.rest = { perched: r1.perched, rafTicksIn5s: r1.metrics.rafTicks - r0.metrics.rafTicks, mainThreadMsPerSec: +(((mr1.TaskDuration - mr0.TaskDuration) * 1000) / 5).toFixed(2) };
console.log(JSON.stringify(out, null, 1));
await browser.close();
server.close();
