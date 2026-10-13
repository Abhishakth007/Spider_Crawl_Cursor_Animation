import { launch } from "./_pw.mjs";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
const b = await launch();
const p = await b.newPage({ viewport: { width: 1000, height: 640 }, deviceScaleFactor: 2 });
await p.goto(pathToFileURL(resolve("index.html")).href + "?debug");
await p.mouse.move(800, 500);
await p.waitForFunction(() => window.__spider && window.__spider.perched, null, { timeout: 20000 });
const results = [];
for (const [dx, dy] of [[3, 3], [-6, 2], [0, -9], [14, 0], [-4, -20], [30, 30]]) {
  const s0 = await p.evaluate(() => window.__spider);
  const px = Math.round(s0.x + 0) , py = 0;
  await p.mouse.move(800 + dx, 500 + dy);
  const t0 = Date.now(); let calm = null, maxW = 0, turns = 0, prevH = null;
  while (Date.now() - t0 < 9000) {
    await p.waitForTimeout(100);
    const s = await p.evaluate(() => window.__spider);
    maxW = Math.max(maxW, Math.abs(s.w));
    if (s.mode === "idle" && s.perched) { calm = Date.now() - t0; break; }
  }
  results.push({ dx, dy, settledMs: calm, maxW: +maxW.toFixed(2) });
  await p.mouse.move(800, 500);   // back, so the next jiggle starts from the same place
  await p.waitForFunction(() => window.__spider.perched, null, { timeout: 15000 }).catch(() => {});
}
console.log(results.map((r) => JSON.stringify(r)).join("\n"));
await b.close();
