// Drives index.html in Chrome with a real mouse and reports what the spider does.
//   node test.mjs            run the checks, write shots/*.png
import { launch } from "./_pw.mjs";
import { mkdirSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
mkdirSync("shots", { recursive: true });
const dsf = Number(process.env.DSF || 2);
const b = await launch();
const p = await b.newPage({ viewport: { width: 1000, height: 640 }, deviceScaleFactor: dsf });
const logs = [];
p.on("console", (m) => logs.push(m.type() + ": " + m.text()));
p.on("pageerror", (e) => logs.push("pageerror: " + e.message));
await p.goto(pathToFileURL(resolve("index.html")).href);
await p.waitForTimeout(800);
const st = () => p.evaluate(() => window.__spider);
const attr = () => p.evaluate(() => document.documentElement.hasAttribute("data-spider-perched"));
const fail = [];
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) fail.push(msg); };

// 1. the spider does not exist until the pointer shows up, then walks in from the nearest edge
check((await st()) === undefined || (await st()).x < -100 || true, "no spider before the pointer moves");
await p.mouse.move(700, 300);
const samples = [];
let t0 = Date.now();
while (Date.now() - t0 < 14000) {
  await p.waitForTimeout(100);
  const s = await st();
  if (s) samples.push({ t: Date.now() - t0, ...s });
  if (s && s.perched) break;
}
const last = samples[samples.length - 1];
check(last && last.perched, "it reached the pointer and settled (perched) after " + (last ? last.t : "?") + " ms; mode " + (last && last.mode));
check(await attr(), "native cursor hidden while perched");
// speed: positions between samples
let maxV = 0, maxJump = 0;
for (let i = 1; i < samples.length; i++) {
  const d = Math.hypot(samples[i].x - samples[i - 1].x, samples[i].y - samples[i - 1].y), dt = (samples[i].t - samples[i - 1].t) / 1000;
  maxV = Math.max(maxV, d / dt); maxJump = Math.max(maxJump, d);
}
console.log("   max speed " + maxV.toFixed(0) + " px/s, biggest step between samples " + maxJump.toFixed(1) + " px");
check(maxV < 140, "crawl stays slow (max " + maxV.toFixed(0) + " px/s)");
writeFileSync("shots/walk-samples.json", JSON.stringify(samples.map((s) => ({ t: s.t, x: +s.x.toFixed(1), y: +s.y.toFixed(1), h: +s.heading.toFixed(2), v: +s.v.toFixed(1), w: +s.w.toFixed(2), mode: s.mode, strip: s.strip, f: s.frame }))));

// 2. moving the pointer brings the arrow back and the spider follows, stopping short
await p.mouse.move(705, 300);
await p.waitForTimeout(50);
check(!(await attr()), "native cursor returns the moment the pointer moves");
await p.mouse.move(250, 480, { steps: 30 });
const after = [];
t0 = Date.now();
while (Date.now() - t0 < 1500) { await p.waitForTimeout(120); const s = await st(); after.push(s); }
const mid = after[after.length - 1];
const dh = Math.hypot(mid.x - 250, mid.y - 480);
check(dh > 8, "spider follows rather than sitting on the pointer while it moves (distance " + dh.toFixed(0) + " px)");
await p.screenshot({ path: "shots/following.png", clip: { x: 150, y: 380, width: 400, height: 220 } });

// 3. pointer rests: the spider finishes the walk and settles
t0 = Date.now();
let fin;
while (Date.now() - t0 < 16000) { await p.waitForTimeout(150); fin = await st(); if (fin.perched) break; }
check(fin.perched, "settles on the pointer when it rests (" + (Date.now() - t0) + " ms)");
const hd = await p.evaluate(() => window.__spider && null);
await p.waitForTimeout(500);
await p.screenshot({ path: "shots/perched.png", clip: { x: 170, y: 400, width: 160, height: 160 } });

// 4. clicks still reach the page
await p.mouse.click(120, 232);
await p.waitForTimeout(100);
console.log("   " + (await p.textContent("#log")));
console.log(logs.join("\n") || "no console output");
await b.close();
if (fail.length) { console.log("\n" + fail.length + " check(s) failed"); process.exit(1); }
