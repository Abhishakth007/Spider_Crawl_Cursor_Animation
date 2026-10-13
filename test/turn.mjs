// A 180: let the spider settle, put the pointer straight behind it, and log how it gets round. Also writes a filmstrip.
//   node test/turn.mjs [url]
import { launch } from "./_pw.mjs";
import { mkdirSync, rmSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
const url = process.argv[2] || pathToFileURL(resolve("index.html")).href + "?debug";
const out = "shots/turn"; rmSync(out, { recursive: true, force: true }); mkdirSync(out, { recursive: true });
const b = await launch();
const p = await b.newPage({ viewport: { width: 1000, height: 640 }, deviceScaleFactor: 2 });
await p.goto(url);
await p.mouse.move(500, 330);
await p.waitForFunction(() => window.__spider && window.__spider.perched, null, { timeout: 25000 });
await p.waitForTimeout(600);
const s0 = await p.evaluate(() => window.__spider);
// the pointer goes straight behind the spider, 260 px away
const dir = [-Math.sin(s0.heading), Math.cos(s0.heading)];
const tx = Math.max(60, Math.min(940, s0.x + dir[0] * 260)), ty = Math.max(60, Math.min(580, s0.y + dir[1] * 260));
console.log("heading", s0.heading.toFixed(2), "pointer ->", tx.toFixed(0), ty.toFixed(0));
await p.mouse.move(tx, ty);
const rows = []; const t0 = Date.now(); let n = 0;
while (Date.now() - t0 < 7000) {
  const s = await p.evaluate(() => window.__spider);
  rows.push({ t: (Date.now() - t0) / 1000, ...s });
  if (n < 70) { const R = 62; await p.screenshot({ path: `${out}/f${String(n++).padStart(3, "0")}.png`, clip: { x: Math.max(0, Math.min(1000 - 2 * R, s.x - R)), y: Math.max(0, Math.min(640 - 2 * R, s.y - R)), width: 2 * R, height: 2 * R } }); }
  await p.waitForTimeout(60);
}
const first = rows[0]; let turned = 0, prev = first.heading, minV = 1e9, path = 0, lastIdx = 0;
let t90 = null, t180 = null;
for (const r of rows) {
  const d = Math.atan2(Math.sin(r.heading - prev), Math.cos(r.heading - prev)); turned += d; prev = r.heading;
  if (t90 === null && Math.abs(turned) > Math.PI / 2) t90 = r.t;
  if (t180 === null && Math.abs(turned) > Math.PI * 0.95) { t180 = r.t; lastIdx = rows.indexOf(r); }
}
for (let i = 1; i <= lastIdx; i++) { path += Math.hypot(rows[i].x - rows[i - 1].x, rows[i].y - rows[i - 1].y); minV = Math.min(minV, rows[i].v); }
const seq = []; for (const r of rows) { if (!seq.length || seq[seq.length - 1] !== r.strip) seq.push(r.strip); }
console.log("90 deg at", t90 && t90.toFixed(2), "s; 180 deg at", t180 && t180.toFixed(2), "s");
console.log("distance walked during the turn", path.toFixed(0), "px; slowest forward speed during it", minV.toFixed(1), "px/s");
const span = rows.slice(0, lastIdx + 1); const xs = span.map((r) => r.x), ys = span.map((r) => r.y);
console.log("the turn took up a box", (Math.max(...xs) - Math.min(...xs)).toFixed(0), "x", (Math.max(...ys) - Math.min(...ys)).toFixed(0), "px; max yaw rate", Math.max(...rows.map((r) => Math.abs(r.w))).toFixed(2), "rad/s");
console.log("strips in order:", seq.join(" > "));
await b.close();
