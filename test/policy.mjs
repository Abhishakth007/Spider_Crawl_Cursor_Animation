import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import http from "node:http";
import path from "node:path";

const root = path.resolve(new URL("..", import.meta.url).pathname.replace(/^\/(\w:)/, "$1"));
import { chromium } from "./_pw.mjs";
const group = process.argv.includes("--group") ? process.argv[process.argv.indexOf("--group") + 1] : "all";
const mime = { ".js": "text/javascript", ".json": "application/json", ".webp": "image/webp", ".html": "text/html" };

const defaultsHtml = `<!doctype html><meta name="viewport" content="width=device-width"><button id="core">core works</button><output id="out">ready</output>
<script src="/spider-cursor.js"></script><script>window.spider=SpiderCursor.create({debug:true});</script>`;
const html = `<!doctype html><meta name="viewport" content="width=device-width"><button id="core">core works</button><output id="out">ready</output>
<script src="/spider-cursor.js"></script><script>
core.onclick=()=>out.textContent="clicked";
window.spider=SpiderCursor.create({src:"/assets/",liteSrc:"/assets-lite/",debug:true,fidget:"auto",quality:"lite",preload:false,prefetch:false,motion:"auto",cacheBytes:8*1024*1024});
</script>`;

let blockAssets = false;
let assetDelayMs = 0;
const server = http.createServer(async (req, res) => {
  const pathname = new URL(req.url, "http://127.0.0.1").pathname;
  if (pathname === "/default.html") { res.writeHead(200, { "content-type": "text/html", "cache-control": "no-store" }); res.end(defaultsHtml); return; }
  if (pathname === "/test.html") { res.writeHead(200, { "content-type": "text/html", "cache-control": "no-store" }); res.end(html); return; }
  if (blockAssets && /^\/(?:assets|assets-lite)\//.test(pathname)) { res.writeHead(503).end("blocked"); return; }
  if (assetDelayMs && /\/(?:assets|assets-lite)\/\d+\/[^/]+\.webp$/.test(pathname)) await new Promise((resolve) => setTimeout(resolve, assetDelayMs));
  try {
    const file = path.resolve(root, pathname.replace(/^\/+/, ""));
    if (!file.toLowerCase().startsWith(root.toLowerCase() + path.sep)) throw new Error("outside root");
    const body = await readFile(file);
    res.writeHead(200, { "content-type": mime[path.extname(file)] || "application/octet-stream", "cache-control": "no-store", "content-length": body.length });
    res.end(body);
  } catch { res.writeHead(404).end("not found"); }
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ channel: "chrome", headless: true });

function spiderRequests(requests) {
  return requests.filter((url) => /\/(?:assets|assets-lite)\/.+(?:manifest\.json|\.webp)$/.test(url));
}

async function withPage(contextOptions, fn, { url = "/test.html", init } = {}) {
  const context = await browser.newContext({ viewport: { width: 900, height: 600 }, ...contextOptions });
  const page = await context.newPage();
  const requests = [];
  page.on("request", (request) => requests.push(request.url()));
  if (init) await page.addInitScript(init);
  await page.goto(origin + url);
  try { await fn(page, requests); } finally { await context.close(); }
}

const tests = [];
function test(name, testGroup, fn) { if (group === "all" || group === testGroup) tests.push({ name, fn }); }

test("defers every Spider asset request until an eligible pointer event", "eligibility", async () => {
  await withPage({}, async (page, requests) => {
    await page.waitForTimeout(500);
    assert.equal(spiderRequests(requests).length, 0);
    await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
    await page.waitForFunction(() => window.__spider?.ready === true);
    assert.ok(spiderRequests(requests).length > 0);
  });
});

test("ignores touch by default but accepts a real mouse on a touch-capable hybrid", "eligibility", async () => {
  await withPage({ hasTouch: true }, async (page, requests) => {
    await page.dispatchEvent("body", "pointermove", { pointerType: "touch", clientX: 200, clientY: 200 });
    await page.waitForTimeout(300);
    assert.equal(spiderRequests(requests).length, 0);
    await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
    await page.waitForFunction(() => window.__spider?.ready === true);
    assert.ok(spiderRequests(requests).length > 0);
  });
});

test("keeps core content usable when every Spider asset is blocked", "eligibility", async () => {
  blockAssets = true;
  try {
    await withPage({}, async (page) => {
      await page.click("#core");
      assert.equal(await page.textContent("#out"), "clicked");
      await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
      await page.waitForTimeout(500);
      assert.equal(await page.textContent("#out"), "clicked");
    });
  } finally { blockAssets = false; }
});

test("loads only manifest plus walk and calm-idle for first use", "loading", async () => {
  await withPage({}, async (page, requests) => {
    await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
    await page.waitForFunction(() => window.__spider?.ready === true);
    await page.waitForTimeout(500);
    const assetRequests = spiderRequests(requests);
    assert.equal(assetRequests.filter((url) => url.endsWith(".webp")).length, 2, assetRequests.join("\n"));
    assert.ok(assetRequests.some((url) => url.endsWith("/walk0.webp")));
    assert.ok(assetRequests.some((url) => url.endsWith("/idle_calm.webp")));
  });
});

test("does not run a recurring animation loop before input or while API-hidden", "lifecycle", async () => {
  const context = await browser.newContext({ viewport: { width: 900, height: 600 } });
  const page = await context.newPage();
  await page.addInitScript(() => {
    const native = window.requestAnimationFrame.bind(window);
    window.__allRaf = 0;
    window.requestAnimationFrame = (cb) => native((time) => { window.__allRaf++; cb(time); });
  });
  await page.goto(origin + "/test.html");
  await page.evaluate(() => { window.__allRaf = 0; });
  await page.waitForTimeout(300);
  assert.ok(await page.evaluate(() => window.__allRaf <= 1), "rAF continued before input");
  await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
  await page.waitForFunction(() => window.__spider?.ready === true);
  await page.evaluate(() => { spider.hide(); window.__allRaf = 0; });
  await page.waitForTimeout(300);
  assert.ok(await page.evaluate(() => window.__allRaf <= 1), "rAF continued while API-hidden");
  await context.close();
});

test("keeps the native cursor hidden while another instance remains perched", "lifecycle", async () => {
  await withPage({}, async (page) => {
    await page.evaluate(() => { window.second = SpiderCursor.create({ src: "/assets/", spawn: "pointer", fidget: false, debug: true }); });
    await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 450, clientY: 300 });
    await page.waitForFunction(() => window.spider.state().perched && window.second.state().perched, null, { timeout: 20_000 });
    assert.equal(await page.evaluate(() => document.documentElement.hasAttribute("data-spider-perched")), true);
    await page.evaluate(() => { window.second.destroy(); window.second.destroy(); });
    assert.equal(await page.evaluate(() => window.spider.state().perched), true);
    assert.equal(await page.evaluate(() => document.documentElement.hasAttribute("data-spider-perched")), true);
  });
});

test("cancels pending work and starts no new tier fetches while hidden", "lifecycle", async () => {
  assetDelayMs = 500;
  try {
    await withPage({}, async (page, requests) => {
      await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
      await page.waitForFunction(() => spider.state().cache.pending > 0);
      await page.evaluate(() => { spider.hide(); spider.setSize(90); });
      const issued = spiderRequests(requests).length;
      await page.waitForTimeout(700);
      assert.deepEqual(await page.evaluate(() => { const c = spider.state().cache; return { pending: c.pending, queued: c.queued }; }), { pending: 0, queued: 0 });
      assert.equal(spiderRequests(requests).length, issued);
      await page.evaluate(() => spider.show());
      await page.waitForFunction(() => spider.state().ready === true, null, { timeout: 20_000 });
    });
  } finally { assetDelayMs = 0; }
});

test("destroy during decode cannot publish stale work", "lifecycle", async () => {
  assetDelayMs = 500;
  try {
    await withPage({}, async (page) => {
      await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
      await page.waitForFunction(() => spider.state().cache.pending > 0);
      await page.evaluate(() => spider.destroy());
      await page.waitForTimeout(700);
      const result = await page.evaluate(() => { const c = spider.state().cache; return { pending: c.pending, queued: c.queued, canvases: document.querySelectorAll("canvas").length, perched: document.documentElement.hasAttribute("data-spider-perched") }; });
      assert.deepEqual(result, { pending: 0, queued: 0, canvases: 0, perched: false });
    });
  } finally { assetDelayMs = 0; }
});

test("quality lite uses the lite profile and only its two critical sheets", "policy", async () => {
  await withPage({}, async (page, requests) => {
    await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
    await page.waitForFunction(() => window.spider.state().ready === true, null, { timeout: 20_000 });
    const state = await page.evaluate(() => window.spider.state());
    assert.equal(state.effectiveQuality, "lite");
    assert.ok(state.tier <= 128);
    const webp = spiderRequests(requests).filter((url) => url.endsWith(".webp"));
    assert.equal(webp.length, 2, webp.join("\n"));
    assert.ok(webp.every((url) => url.includes("/assets-lite/")));
  });
});

test("reduced motion loads one still, never perches, and becomes quiescent", "policy", async () => {
  const context = await browser.newContext({ viewport: { width: 900, height: 600 }, reducedMotion: "reduce" });
  const page = await context.newPage();
  const requests = [];
  await page.addInitScript(() => {
    const native = window.requestAnimationFrame.bind(window);
    window.__allRaf = 0;
    window.requestAnimationFrame = (cb) => native((time) => { window.__allRaf++; cb(time); });
  });
  page.on("request", (request) => requests.push(request.url()));
  await page.goto(origin + "/test.html");
  await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
  await page.waitForFunction(() => window.spider.state().ready === true, null, { timeout: 20_000 });
  const state = await page.evaluate(() => window.spider.state());
  assert.equal(state.effectiveMotion, "reduced");
  assert.equal(state.perched, false);
  const webp = spiderRequests(requests).filter((url) => url.endsWith(".webp"));
  assert.equal(webp.length, 1, webp.join("\n"));
  assert.ok(webp[0].endsWith("/idle_still.webp"));
  await page.evaluate(() => { window.__allRaf = 0; });
  await page.waitForTimeout(300);
  assert.ok(await page.evaluate(() => window.__allRaf <= 1), "reduced mode kept scheduling frames");
  await context.close();
});

test("motion off performs no fetch even after mouse input", "policy", async () => {
  await withPage({}, async (page, requests) => {
    await page.evaluate(() => { window.spider.destroy(); window.spider = SpiderCursor.create({ src: "/assets/", liteSrc: "/assets-lite/", motion: "off", debug: true }); });
    await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
    await page.waitForTimeout(300);
    assert.equal(spiderRequests(requests).length, 0);
  });
});

test("fully settled auto mode has no recurring library rAF", "policy", async () => {
  await withPage({}, async (page) => {
    await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
    await page.waitForFunction(() => window.spider.state().perched === true, null, { timeout: 25_000 });
    await page.waitForTimeout(400); // allow the final deceleration frames after the perch transition
    const before = await page.evaluate(() => window.spider.state().metrics?.rafTicks ?? -1);
    assert.ok(before >= 0, "metrics.rafTicks is not exposed");
    await page.waitForTimeout(500);
    const after = await page.evaluate(() => window.spider.state().metrics?.rafTicks ?? -1);
    assert.ok(after - before <= 1, `idle rAF ticks: ${after - before}`);
  });
});

test("rapid tier A-B-A changes publish only the final tier within budget", "races", async () => {
  assetDelayMs = 350;
  try {
    await withPage({}, async (page) => {
      await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
      await page.waitForFunction(() => { const s = spider.state(); return s.tier === 96 && s.cache.pending > 0; });
      await page.evaluate(() => spider.setSize(90));
      await page.waitForFunction(() => spider.state().tier === 128);
      await page.evaluate(() => spider.setSize(34));
      await page.waitForFunction(() => { const s = spider.state(); return s.ready && s.tier === 96 && s.cache.pending === 0; }, null, { timeout: 20_000 });
      const state = await page.evaluate(() => spider.state());
      assert.equal(state.tier, 96);
      assert.ok(state.cache.bytes <= state.cache.limit, JSON.stringify(state.cache));
    });
  } finally { assetDelayMs = 0; }
});

test("full-quality cache uses a bounded documented working-set floor", "races", async () => {
  assetDelayMs = 900;
  try {
    await withPage({}, async (page, requests) => {
      await page.evaluate(() => { spider.destroy(); window.spider = SpiderCursor.create({ src: "/assets/", liteSrc: "/assets-lite/", quality: "full", motion: "full", fidget: true, spawn: "pointer", size: 90, cacheBytes: 32 * 1024 * 1024 }); });
      await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 450, clientY: 300 });
      await page.waitForFunction(() => spider.state().ready === true, null, { timeout: 30_000 });
      await page.evaluate(() => { window.__cacheSamples = []; window.__cacheSampler = setInterval(() => __cacheSamples.push(spider.state().cache), 10); });
      for (const point of [[450, 80], [820, 300], [450, 540], [80, 300], [800, 100], [100, 500], [800, 500], [100, 100]]) { await page.mouse.move(...point); await page.waitForTimeout(120); }
      await page.waitForFunction(() => { const c = spider.state().cache; return c.pending === 0 && c.queued === 0; }, null, { timeout: 30_000 });
      const result = await page.evaluate(() => { clearInterval(__cacheSampler); return { cache: spider.state().cache, samples: __cacheSamples }; });
      assert.ok(spiderRequests(requests).filter((url) => url.endsWith(".webp")).length >= 3);
      assert.ok(result.samples.some((cache) => cache.queued > 1), "optional demand did not overlap");
      assert.ok(result.samples.every((cache) => cache.bytes <= cache.limit), "cache exceeded its effective limit during overlap");
      assert.ok(result.cache.limit >= result.cache.configuredLimit);
      assert.ok(result.cache.bytes <= result.cache.limit, `${result.cache.bytes} > ${result.cache.limit}`);
    });
  } finally { assetDelayMs = 0; }
});

test("a live reduced-motion change cannot revive stale normal assets", "races", async () => {
  await withPage({}, async (page) => {
    await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.waitForFunction(() => { const s = spider.state(); return s.effectiveMotion === "reduced" && s.ready; }, null, { timeout: 20_000 });
    await page.waitForTimeout(500);
    const state = await page.evaluate(() => spider.state());
    assert.equal(state.effectiveMotion, "reduced");
    assert.equal(state.strip, "idle_still");
    assert.equal(await page.evaluate(() => document.documentElement.hasAttribute("data-spider-perched")), false);
  });
});

test("twenty create-destroy cycles restore DOM counts", "lifecycle", async () => {
  await withPage({}, async (page) => {
    const result = await page.evaluate(() => {
      const before = { canvases: document.querySelectorAll("canvas").length, styles: document.querySelectorAll("style").length };
      for (let i = 0; i < 20; i++) SpiderCursor.create({ src: "/assets/", motion: "off" }).destroy();
      return { before, after: { canvases: document.querySelectorAll("canvas").length, styles: document.querySelectorAll("style").length } };
    });
    assert.deepEqual(result.after, result.before);
  });
});


// ---- what the merge adds: full quality by default, and the cheap ways of keeping it

test("the default is full quality (and every sheet comes from assets/, not assets-lite/)", "merge", async () => {
  await withPage({}, async (page, requests) => {
    await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
    await page.waitForFunction(() => window.spider.state().ready === true, null, { timeout: 20_000 });
    const state = await page.evaluate(() => window.spider.state());
    assert.equal(state.effectiveQuality, "full");
    assert.ok(spiderRequests(requests).filter((url) => url.endsWith(".webp")).every((url) => !url.includes("/assets-lite/")));
  }, { url: "/default.html" });
});

test("a browser that asks to save data, or reports little memory, gets lite by default; an explicit quality wins", "merge", async () => {
  for (const init of [
    () => Object.defineProperty(navigator, "connection", { value: { saveData: true, effectiveType: "4g" } }),
    () => Object.defineProperty(navigator, "connection", { value: { saveData: false, effectiveType: "2g" } }),
    () => Object.defineProperty(navigator, "deviceMemory", { value: 1 }),
  ]) {
    await withPage({}, async (page) => {
      assert.equal(await page.evaluate(() => window.spider.state().effectiveQuality), "lite");
      await page.evaluate(() => { window.spider.destroy(); window.spider = SpiderCursor.create({ quality: "full", debug: true }); });
      assert.equal(await page.evaluate(() => window.spider.state().effectiveQuality), "full");
    }, { url: "/default.html", init });
  }
});

test("on a desktop the two critical sheets are preloaded while idle, with no animation loop, and nothing else", "merge", async () => {
  const context = await browser.newContext({ viewport: { width: 900, height: 600 } });
  const page = await context.newPage();
  const requests = [];
  page.on("request", (request) => requests.push(request.url()));
  await page.addInitScript(() => {
    const native = window.requestAnimationFrame.bind(window);
    window.__allRaf = 0;
    window.requestAnimationFrame = (cb) => native((time) => { window.__allRaf++; cb(time); });
  });
  await page.goto(origin + "/default.html");
  await page.waitForTimeout(1500);
  const webp = spiderRequests(requests).filter((url) => url.endsWith(".webp")).map((url) => url.split("/").pop()).sort();
  assert.deepEqual(webp, ["idle_calm.webp", "walk0.webp"]);
  assert.equal(spiderRequests(requests).filter((url) => url.endsWith("manifest.json")).length, 0, "no manifest request by default");
  assert.equal(await page.evaluate(() => document.querySelectorAll("canvas").length >= 0 && window.__allRaf <= 3), true, "a loop ran before any input");
  assert.equal(await page.evaluate(() => getComputedStyle(document.querySelector("canvas")).opacity), "0", "visible before any input");
  await context.close();
});

test("a phone (no mouse) preloads nothing, not even after a tap", "merge", async () => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  const requests = [];
  page.on("request", (request) => requests.push(request.url()));
  await page.goto(origin + "/default.html");
  await page.waitForTimeout(1500);
  await page.touchscreen.tap(200, 400);
  await page.waitForTimeout(500);
  assert.equal(spiderRequests(requests).length, 0, spiderRequests(requests).join("\n"));
  await context.close();
});

test("after it appears, the curved-walk sheets are prefetched within the budget and the first turn does not wait", "merge", async () => {
  await withPage({}, async (page, requests) => {
    await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
    await page.waitForFunction(() => { const c = window.spider.state().cache; return window.spider.state().ready && c.pending === 0 && c.queued === 0 && c.entries >= 4; }, null, { timeout: 25_000 });
    const names = spiderRequests(requests).filter((url) => url.endsWith(".webp")).map((url) => url.split("/").pop().replace(".webp", ""));
    for (const n of ["walk0", "idle_calm", "walk34", "walk50", "walk18"]) assert.ok(names.includes(n), `${n} not fetched: ${names.join(",")}`);
    const cache = await page.evaluate(() => window.spider.state().cache);
    assert.ok(cache.bytes <= cache.limit, JSON.stringify(cache));
  }, { url: "/default.html" });
});

test("standing, it holds still between fidgets (no loop), ticks at about 24 a second while one plays, and with fidget off never ticks", "merge", async () => {
  await withPage({}, async (page) => {
    await page.dispatchEvent("body", "pointermove", { pointerType: "mouse", clientX: 500, clientY: 300 });
    await page.waitForFunction(() => window.spider.state().perched === true, null, { timeout: 25_000 });
    await page.waitForFunction(() => window.spider.state().idle === "idle_calm", null, { timeout: 15_000 });
    await page.waitForTimeout(400);
    // still: wait for a quiet second between fidgets and count
    let still = null;
    for (let i = 0; i < 14 && still === null; i++) {
      const a = await page.evaluate(() => ({ t: window.spider.state().metrics.rafTicks, idle: window.spider.state().idle }));
      await page.waitForTimeout(1000);
      const b = await page.evaluate(() => ({ t: window.spider.state().metrics.rafTicks, idle: window.spider.state().idle }));
      if (a.idle === "idle_calm" && b.idle === "idle_calm") still = b.t - a.t;
    }
    assert.ok(still !== null && still <= 1, `still spider ticked ${still} times in a second`);
    // a fidget: wait for one to start, then count a second of it
    await page.waitForFunction(() => window.spider.state().idle !== "idle_calm", null, { timeout: 25_000 });
    const f0 = await page.evaluate(() => window.spider.state().metrics.rafTicks);
    await page.waitForTimeout(1000);
    const f1 = await page.evaluate(() => window.spider.state().metrics.rafTicks);
    assert.ok(f1 - f0 >= 10 && f1 - f0 <= 45, `a playing fidget ticked ${f1 - f0} times in a second`);
    await page.evaluate(() => window.spider.set({ fidget: false }));
    await page.waitForTimeout(800);
    const c = await page.evaluate(() => window.spider.state().metrics.rafTicks);
    await page.waitForTimeout(1500);
    const d = await page.evaluate(() => window.spider.state().metrics.rafTicks);
    assert.ok(d - c <= 1, `fidget off still ticked ${d - c} times`);
  }, { url: "/default.html" });
});

test("the arrow-hiding style is a constructed stylesheet (no <style> element, so a strict CSP cannot block it) and is removed on destroy", "merge", async () => {
  await withPage({}, async (page) => {
    const before = await page.evaluate(() => ({ sheets: document.adoptedStyleSheets.length, styles: document.querySelectorAll("style").length }));
    assert.equal(before.sheets, 1);
    assert.equal(before.styles, 0);
    await page.evaluate(() => window.spider.destroy());
    assert.equal(await page.evaluate(() => document.adoptedStyleSheets.length), 0);
  }, { url: "/default.html" });
});

let failed = 0;
for (const { name, fn } of tests) {
  try { await fn(); console.log("PASS", name); }
  catch (error) { failed++; console.error("FAIL", name, "\n ", error.stack || error); }
}
await browser.close();
server.close();
if (failed) process.exitCode = 1;
