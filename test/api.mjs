import { launch } from "./_pw.mjs";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
const b = await launch();
const errs = [];
async function run(name, ctxOpts, create, fn) {
  const ctx = await b.newContext({ viewport: { width: 900, height: 600 }, deviceScaleFactor: 2, ...ctxOpts });
  const p = await ctx.newPage();
  p.on("console", (m) => { if (m.type() === "error" || m.type() === "warning") errs.push(name + ": " + m.text()); });
  p.on("pageerror", (e) => errs.push(name + " pageerror: " + e.message));
  await p.goto(pathToFileURL(resolve("index.html")).href);
  await p.evaluate((c) => { window.s2 = SpiderCursor.create(Object.assign({ src: "assets/", debug: false }, c)); }, create);
  await fn(p);
  await ctx.close();
}
// pointer spawn: starts on the pointer and sits there
await run("spawn-pointer", {}, { spawn: "pointer", size: 40 }, async (p) => {
  await p.mouse.move(400, 300);
  await p.waitForTimeout(2500);
  const s = await p.evaluate(() => { const c = [...document.querySelectorAll("canvas")].pop(); const r = c.getBoundingClientRect(); return { cx: r.x + r.width / 2, cy: r.y + r.height / 2, perched: document.documentElement.hasAttribute("data-spider-perched"), pos: window.s2.position() }; });
  console.log("spawn pointer:", JSON.stringify({ perched: s.perched, head: s.pos.head, pivot: [s.pos.x, s.pos.y] }));
});
// reduced motion: one still frame at the pointer; it does not walk, perch or run a loop
await run("reduced", { reducedMotion: "reduce" }, { size: 34 }, async (p) => {
  await p.mouse.move(700, 450);
  await p.waitForTimeout(1500);
  const s = await p.evaluate(() => window.s2.state());
  const near = await p.evaluate(() => { const q = window.s2.position(); return Math.hypot(q.head.x - 700, q.head.y - 450); });
  console.log("reduced motion: motion=" + s.effectiveMotion + " strip=" + s.strip + " perched=" + s.perched + " ticks=" + s.metrics.rafTicks + " head " + near.toFixed(0) + " px from the pointer");
  if (!(s.effectiveMotion === "reduced" && s.strip === "idle_still" && !s.perched && near < 4)) { console.log("FAIL reduced motion"); process.exitCode = 1; }
});
// destroy cleans up
await run("destroy", {}, { size: 34 }, async (p) => {
  await p.mouse.move(300, 300); await p.waitForTimeout(500);
  const before = await p.evaluate(() => document.querySelectorAll("canvas").length);
  await p.evaluate(() => window.s2.destroy());
  const after = await p.evaluate(() => ({ c: document.querySelectorAll("canvas").length, perched: document.documentElement.hasAttribute("data-spider-perched"), styles: document.querySelectorAll("style").length }));
  console.log("destroy: canvases", before, "->", after.c, "perched attr", after.perched);
});
console.log(errs.length ? "console problems:\n" + errs.join("\n") : "no console errors or warnings");
await b.close();
