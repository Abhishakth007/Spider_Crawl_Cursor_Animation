import { launch } from "./_pw.mjs";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
import { writeFileSync } from "node:fs";
const b = await launch();
const p = await b.newPage({ viewport: { width: 1000, height: 640 }, deviceScaleFactor: 2 });
await p.goto(pathToFileURL(resolve("index.html")).href);
await p.mouse.move(500, 320);
await p.waitForFunction(() => window.__spider && window.__spider.perched, null, { timeout: 20000 });
const rows = []; const t0 = Date.now();
const path = (t) => {  // 0-6 s circle, 6-9 s zig-zag across, 9-12 s stop
  if (t < 6) { const a = t * 1.3; return [500 + 220 * Math.cos(a), 320 + 160 * Math.sin(a)]; }
  if (t < 9) { const k = (t - 6) / 3; return [100 + 800 * k, 320 + 200 * Math.sin(k * 18)]; }
  return [900, 320];
};
while (Date.now() - t0 < 24000) {
  const t = (Date.now() - t0) / 1000;
  const [x, y] = path(Math.min(t, 10));
  await p.mouse.move(x, y);
  const s = await p.evaluate(() => window.__spider);
  rows.push({ t, px: x, py: y, ...s });
  await p.waitForTimeout(30);
}
let maxW = 0, maxV = 0, maxJump = 0;
for (let i = 1; i < rows.length; i++) { maxW = Math.max(maxW, Math.abs(rows[i].w)); maxV = Math.max(maxV, rows[i].v); maxJump = Math.max(maxJump, Math.hypot(rows[i].x - rows[i-1].x, rows[i].y - rows[i-1].y)); }
const modes = {}; rows.forEach((r) => (modes[r.strip] = (modes[r.strip] || 0) + 1));
console.log("maxW", maxW.toFixed(2), "maxV", maxV.toFixed(0), "maxJump(px/sample)", maxJump.toFixed(1), "strips", JSON.stringify(modes));
const last = rows[rows.length - 1]; console.log("end", last.mode, "perched", last.perched, "dist to pointer", Math.hypot(last.x - 900, last.y - 320).toFixed(0));
const minD = Math.min(...rows.filter(r=>r.t<9).map((r) => Math.hypot(r.x - r.px, r.y - r.py)));
console.log("closest approach to a moving pointer (pivot to pointer)", minD.toFixed(0), "px");
await b.close();
