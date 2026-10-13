// The black widow, loaded the way a stranger would: data-skin on the one-liner, from jsDelivr, on a page from another origin.
//   node test/cdn-widow.mjs [version]
import http from "node:http";
import { readFileSync } from "node:fs";
import { launch } from "./_pw.mjs";

const major = (process.argv[2] || JSON.parse(readFileSync("package.json", "utf8")).version).split(".")[0];
const page_html = `<!doctype html><body style="margin:0;height:100vh;background:#16181e"><script src="https://cdn.jsdelivr.net/npm/spider-crawl-cursor@${major}/spider-cursor.min.js" data-skin="widow" data-size="48"></script>`;
const server = http.createServer((req, res) => { res.writeHead(200, { "content-type": "text/html" }); res.end(page_html); });
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const browser = await launch();
const page = await browser.newPage({ viewport: { width: 1000, height: 640 }, deviceScaleFactor: 2 });
const sheets = [], problems = [];
page.on("request", (r) => { if (/spider-crawl-cursor.*\.webp$/.test(r.url())) sheets.push(r.url().split("/npm/")[1]); });
page.on("console", (m) => { if (["error", "warning"].includes(m.type())) problems.push(m.text()); });
await page.goto(`http://127.0.0.1:${server.address().port}/`);
await page.mouse.move(300, 300);
await page.mouse.move(600, 380, { steps: 25 });
await new Promise((r) => setTimeout(r, 4000));
const pixels = await page.evaluate(() => { const c = document.querySelector("canvas"); if (!c) return -1; const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 20) n++; return n; });
const widow = sheets.filter((s) => /assets-widow\//.test(s)).length;
console.log(`sheets requested: ${sheets.length} (${widow} from assets-widow/); drawn pixels: ${pixels}; console problems: ${problems.length}`);
console.log(sheets.slice(0, 3).join("\n"));
await browser.close(); server.close();
if (widow === 0 || sheets.some((s) => !/assets-widow/.test(s) && !/assets-widow-lite/.test(s)) || pixels < 500 || problems.length) { console.log("FAILED"); process.exit(1); }
console.log("ok: data-skin=\"widow\" loads the widow sheets from the CDN and draws the spider");
