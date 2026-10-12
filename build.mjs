// Builds the files people actually load from src/spider-cursor.js:
//
//   spider-cursor.js       the readable one, for a <script> tag (finds assets/ next to itself)
//   spider-cursor.min.js   the same, minified (this is what the CDN one-liner serves)
//   spider-cursor.mjs      for `import` in a bundler  (it cannot know where it was loaded from, so its sprites come from the CDN)
//   spider-cursor.cjs      for `require`               (same)
//
// Every one is stamped with the package version, so the CDN address the bundler builds use is pinned to the release they came from.
//   node build.mjs
import { readFileSync, writeFileSync } from "node:fs";
import { transform } from "esbuild";

const pkg = JSON.parse(readFileSync("package.json", "utf8"));
const src = readFileSync("src/spider-cursor.js", "utf8");
if (!src.includes('"__VERSION__"')) throw new Error("src/spider-cursor.js has lost its version placeholder");

const stamped = src.replace('"__VERSION__"', JSON.stringify(pkg.version));
const SELF = /\/\*SELF\*\/[\s\S]*?\/\*ENDSELF\*\//;
if (!SELF.test(stamped)) throw new Error("src/spider-cursor.js has lost its SELF markers");
const blind = stamped.replace(SELF, '""');            // no document.currentScript: the code is inside somebody's bundle

const esm = `${blind}\nexport default module.exports;\nexport const create = module.exports.create;\nexport const version = module.exports.version;\n`
  .replace('(function (root, factory) {', 'var module = { exports: {} };\n(function (root, factory) {');

writeFileSync("spider-cursor.js", stamped);
writeFileSync("spider-cursor.cjs", blind);
writeFileSync("spider-cursor.mjs", esm);
const min = await transform(stamped, { minify: true, legalComments: "inline", target: "es2017" });
writeFileSync("spider-cursor.min.js", min.code);

for (const f of ["spider-cursor.js", "spider-cursor.min.js", "spider-cursor.mjs", "spider-cursor.cjs"]) {
  console.log(f.padEnd(24), (readFileSync(f).length / 1024).toFixed(1) + " KB");
}
console.log("version", pkg.version);
