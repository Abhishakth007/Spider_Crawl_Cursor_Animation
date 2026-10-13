# Spider crawl cursor

[![npm](https://img.shields.io/npm/v/spider-crawl-cursor?color=f2a30a)](https://www.npmjs.com/package/spider-crawl-cursor)
[![license](https://img.shields.io/npm/l/spider-crawl-cursor?color=26231e)](LICENSE)

![the spider](hero.png)

A spider that follows your cursor. Modelled, furred and rendered in Blender (Cycles, on the GPU); the page only plays the frames back. It walks the way a real one does (the gait was taken from a reference walk cycle, foot by foot), it stands on the page with a soft shadow of its own, and there are two skins: a red-and-blue spider and a black widow.
It is its own animal: your pointer stays your pointer, and the spider crawls after it, slowly, the way a real one does.

**[Try it live](https://abhishakth007.github.io/Spider_Crawl_Cursor_Animation/)**, and if you do, **[rate it](https://github.com/Abhishakth007/Spider_Crawl_Cursor_Animation/issues/new?template=feedback.yml)** (one minute, a 1-5 rating and a few words).

## Put it on your page

One line. Nothing to host, no build step:

```html
<script src="https://cdn.jsdelivr.net/npm/spider-crawl-cursor@1/spider-cursor.min.js"></script>
```

That is all: it starts itself and finds its own sprites. It only fetches what it needs: on a desktop two small sheets once the page is idle (so the spider is there the moment the mouse first moves), and on a phone, which has no mouse, nothing at all.
Options go on the tag:

```html
<script src="https://cdn.jsdelivr.net/npm/spider-crawl-cursor@1/spider-cursor.min.js" data-size="40" data-speed="1.5"></script>
```

Other ways:

```bash
npm i spider-crawl-cursor
```

```js
import SpiderCursor from "spider-crawl-cursor";
const spider = SpiderCursor.create({ size: 40 });   // its sprites come from the CDN; pass src to host them yourself
// spider.destroy() when you leave the page (single-page apps)
```

Or copy the `spider-cursor.min.js` and `assets/` folder next to each other on your own server and use a plain `<script src="spider-cursor.min.js">`: it looks for `assets/` beside itself, wherever the page is.
If you call `SpiderCursor.create()` yourself, the automatic start does not also run; add `data-manual` to the tag to switch it off.

## Options

As `create({ ... })`, or on the script tag as `data-size`, `data-speed`, `data-min-width` ...

| option | default | |
|---|---|---|
| `size` | `34` | body length in CSS px, head to abdomen (the legs reach about 1.8x that). Its speed and stride scale with it |
| `speed` | `1` | `1` is a slow crawl; `2` is twice as fast |
| `perch` | `true` | hide the arrow while the spider sits on the pointer |
| `standoff` | `0.7` | how far short of a moving pointer it stops, in body lengths |
| `spawn` | `"edge"` | `"edge"`: comes in from the nearest edge of the window, starting no further than about 7 body lengths from the pointer. `"pointer"`: starts on the pointer |
| `quality` | `"auto"` | `"full"`: every sprite size and gait. `"lite"`: about a fifth of the data and memory, fewer frames and gaits, softer on a retina screen. `"auto"`: full, unless the browser asks to save data, is on a slow connection or reports little memory |
| `motion` | `"auto"` | `"auto"` honours `prefers-reduced-motion`. Also `"full"`, `"reduced"` (one still frame at the pointer) and `"off"` (nothing is fetched) |
| `fidget` | `"auto"` | now and then, while it stands: a wave, a tap or a groom (on with full quality). `false` makes it perfectly still |
| `preload` | `true` | on a desktop, fetch the two sheets it needs as soon as the page is idle |
| `prefetch` | `true` | once it has appeared, quietly fetch the curved-walk sheets within the memory budget |
| `cacheBytes` | `33554432` | decoded-image memory budget (32 MiB), including images still being decoded |
| `skin` | `"classic"` | `"classic"` (red and blue) or `"widow"` (a black widow). Two sets of sheets rendered from one model and one walk; `data-skin="widow"` on the tag |
| `shadow` | `true` | the sprites carry their own soft shadow, rendered under the feet, so no page shadow is added; `"extra"` adds one anyway, and packs without a baked shadow get the page shadow |
| `bitmap` | `true` | decode each sheet off the main thread (fetch and `createImageBitmap`) where a fetch is certain to be allowed: the page's own origin, jsDelivr, unpkg. Anywhere else it is a plain `<img>` |
| `idleTrim` | `20000` | after the spider has sat still this many ms it gives back the memory of the turning sheets (`0` keeps them) |
| `touch` | `false` | also for touch input (a real mouse on a touch laptop always works) |
| `minWidth` | `0` | do nothing on windows narrower than this many px |
| `src` | next to the script | folder with the sprite sheets (the CDN copy when bundled); the lite sheets are found beside it in `assets-lite/` (`liteSrc`) |
| `manifest` | `false` | read `manifest.json` from `src` (only if you repacked the sheets with other sizes) |

`create()` returns `{ destroy(), set(opts), setSize(px), show(), hide(), position(), state() }`. TypeScript types are included.

## How it behaves

- **It is its own animal.** The pointer stays the pointer. The spider crawls after it (about 2 body lengths a second, a little quicker when the pointer is far away), speeds up and slows down smoothly, and keeps walking until it gets there.
- **It is there at once.** On the first mouse move it appears within a few body lengths of the pointer (it fades in if the edge is far) and scuttles in, quicker than its crawl, so you are looking at it within a second and it has reached the pointer in about three. Then it crawls.
- **It comes up behind you, not onto you.** While you move, it stops about 0.7 body lengths short of the pointer.
- **Hold still and it settles on the pointer.** When the pointer has rested for a moment, the spider walks the last of the way in with its head on the tip. While it sits there the system arrow is hidden (the spider is the cursor); the moment the pointer moves, the arrow is back and the spider is a separate animal again. Clicks, hovers and drags always go to the real pointer.
- **Real gait.** Eight legs in two alternating teams (L1 R2 L3 R4 against R1 L2 R3 L4), each foot on the ground 56 % of the time, so all eight are down twice every cycle. The knees ride high over a low body, the long lower legs drop steeply to the ground, and a lifted foot flicks forward as the leg comes through. The legs run at exactly the speed it travels, so planted feet do not skate, on straights and on curves.
- **It turns like a walking animal.** The sharper the turn, the more it curves, never sharper than an arc about a body length across, so even a 180 is a swing round with the legs still carrying it forward, not a stop, a spin and a restart. The body bends into the turn (the head leads, the abdomen trails out the far side) and the yaw comes in steps with the legs. Only when the pointer is too close for an arc does it shuffle round on the spot.
- **Standing, it holds still, as a spider does,** and now and then (every 7 to 16 seconds) it waves a front leg, taps a back one, grooms its fangs or shifts its weight, with its breathing and palp twitches in it. Every standing animation starts and ends on the pose the walk stops in, so there is never a pop. Between fidgets nothing changes, so nothing is drawn and the page does no work for it.
- `prefers-reduced-motion` shows one still frame at the pointer: no walking, no perching, no animation loop. `motion: "off"` fetches nothing. A hidden tab does no work and starts no downloads. Touch input is ignored unless `touch: true`. It works under a strict Content-Security-Policy, and several instances can share the page (the arrow stays hidden while any one of them sits on it).

## Why it stays sharp when it is small

A sprite shrunk by the browser is shrunk with a cheap filter, and thin legs and fur turn to mush. So every size is made ahead of time, properly, from a 768 px master: premultiplied (no dark halo on the edge), Lanczos in half steps, then a little sharpening on the colour. There are sheets at 64, 96, 128, 192 and 256 px per frame (`assets/<size>/`), and the page loads only the one nearest the pixels it needs for the size and the screen's pixel ratio (0.7 to 5.4 MB for the visitor, if every gait is used; the package holds all five). It is also drawn without ever being resampled twice: the canvas sits on whole device pixels and the sub-pixel part is applied inside the draw.

The **lite** sheets (`assets-lite/`, 0.5 MB for all three sizes) trade that away on purpose: 64, 96 and 128 px only, a 16-frame walk instead of 32, three gaits instead of six, no fidgets. On a retina screen they are softer, and its turns are wider. They are what `quality: "auto"` picks when the browser asks to save data, is on a 2G connection, or reports 2 GB of memory or less; everyone else gets full quality.

## What it costs the page

Measured in Chrome (`npm run bench`: a scripted pointer, a 14 s walk with curves, a dash across the window and a rest), on a retina viewport, spider 34 px, full quality. The "before" column is the previous engine playing the same new sprites, so only the engine differs.

| | before (1.1.0 engine) | 1.2.0 |
|---|---|---|
| first visit: sheets fetched before the pointer moves | 642 KB | **306 KB** (the standing pose is one frame, not forty-eight) |
| a whole walking session, curves included | 2.1 MB, a sheet fetched up to three times | **1.7 MB**, each sheet once |
| the first time each gait is drawn | a 14 to 21 ms frame (the browser decodes the sheet again, on the main thread, in the middle of the frame) | **no hitch**: every frame lands on the display interval, the slowest in 14 s was 7.5 ms |
| decoded image memory while walking | 29 MB | 28 MB |
| decoded image memory once it has settled | 29 MB, kept | **5.6 MB** (the turning sheets are given back after 20 s and fetched again when it moves) |
| standing, fidgets on | 1.0 % of a core | **0.6 %** |
| standing, fidgets off, or lite | nothing runs | nothing runs |

At 1x display scale the first visit is 119 KB, a session 0.7 MB and the decoded memory 7 MB; `quality: "lite"` is 86 KB, 0.24 MB and 3.5 MB.

The engine behind the numbers: the animation loop is event-driven and stops completely when nothing changes; sheets are fetched and decoded off the main thread, so a gait is ready to draw the moment it arrives; decoded sheets live in a bounded cache and are released when not drawn (a sheet that is already in the cache never re-enters the download queue); the draw path allocates nothing; only the two sheets it needs first are critical, the rest are queued one at a time within the budget; nothing runs in a hidden tab; and stale work from a resize, a destroy or a reduced-motion change can never be published.

## How it was made

`blender/` holds everything that made the frames: Blender 5.2, Cycles on OptiX. A frame takes 3 to 6 seconds on an RTX 5050 laptop GPU at 768 px and 128 samples, so a full set of 452 frames takes 25 to 45 minutes. That cost is paid once; the page just plays the images back.

- `anatomy.py` is every dimension, in Blender units: a 140-unit body, eight 5-piece legs (femur, patella, tibia, metatarsus, tarsus), the hips, the eyes, and the gait numbers.
- `build.py`, `materials.py` and `bl_util.py` build the spider from code: a domed carapace with the jumping-spider eye layout (a big forward pair, two big corner eyes, two tiny, two on the sides) and glassy lenses, chelicerae with fangs, palps, a hanging abdomen, and legs that taper hard and bow gently, with a knuckle at every joint, matte joint membranes, bristles and claws. Colour runs in soft bands along each leg and is painted in plan view on the body (`patterns.py`). Fur is Cycles hair curves in the colour of the skin under them, dense and short on the body and sparse on the legs so the gloss shows through.
- `gait.py` is the walk, as plain maths (numpy, no Blender), taken from a reference walk cycle: the video's foot tips were tracked frame by frame, which gave two alternating tetrapods at about half duty, legs of a team nearly in step with the rear ones a hair ahead, steep femurs, long steep lower legs and a swing that bows outward. A leg is solved from its foot by a 3-link analytic IK. A planted foot is fixed in the world; a swinging foot is eased through the world between where it lifted and where it lands and then expressed in the spider's own frame, which is what keeps it from skating and lets curves and pivots be exact. `pose.py` puts the Blender parts where it says.
- `scene.py` is the render setup: soft, symmetric studio light (so mirrored sprites match), an orthographic camera leaning in from the front at 76 degrees so the face shows, and a shadow-catcher floor lit by its own lights so the shadow is baked into the alpha. `render_sprites.py` renders the 452 frames: six gait strips of 32 (`walk0`, `walk18`, `walk34`, `walk50`, `walk70`, `pivot`) and five standing strips (`idle_calm`, `idle_wave`, `idle_tap`, `idle_groom`, `idle_rock`). It skips frames that already exist, so a long render can be stopped and resumed.
- `lookdev.py` renders stills; `compare_views.py` and `proxy_preview.py` render the model in the reference video's top, side and front views for laying next to its frames; `smallview.py`, `sheet.py` and `strip_sheet.py` show a render at the size it will really be seen, or a whole strip at once.

The gait is tested without Blender (`python test_gait.py` in `blender/`): every leg piece keeps its length in every pose, no leg is asked for more reach than it has, a planted foot stays fixed in the world on straights, curves and pivots, all eight feet are down at phase 0 and 0.5, and the gait at phase + 0.5 is the exact mirror of the gait at phase (the page flips sprites to turn the other way). `test_strips.py` checks that no strip pops between frames and that every standing strip starts and ends on the pose the walk stops in.

```bash
python blender/patterns.py                       # paint the body textures (once)
# render one skin, then pack the sheets for the page (this also rewrites the manifest copy inside src/spider-cursor.js)
blender -b --factory-startup -P blender/render_sprites.py -- renders/master_classic --skin spidey
python pack.py renders/master_classic assets
python pack.py renders/master_classic assets-lite --profile lite
blender -b --factory-startup -P blender/render_sprites.py -- renders/master_widow --skin widow
python pack.py renders/master_widow assets-widow
python pack.py renders/master_widow assets-widow-lite --profile lite
npm install && npm run build                     # the files that are published
```

(`--skin spidey` is the internal name of the red-and-blue skin; the page calls it `classic`.)

## Developing

`src/spider-cursor.js` is the source; `npm run build` writes `spider-cursor.js`, `.min.js`, `.mjs` and `.cjs` from it, stamped with the version.
`test/` drives the page in Chrome with a real mouse (Playwright):

```bash
npm test          # behaviour, jiggle, chase, api, install, policy and trim
npm run bench     # what it costs the page: frame pacing, long tasks, CPU, memory, bytes (node test/trace.mjs shows what the main thread is doing in a long frame)
node test/turn.mjs   # a 180 with the pointer straight behind: how long, how far it walks, which strips
node test/cdn.mjs    # the published package, loaded from jsDelivr by a page on another origin (needs the network)
```

`policy.mjs` covers the engine: nothing fetched before a mouse event, lazy and bounded loading, a hidden tab, destroy during a decode, rapid size changes, reduced motion, shared cursor ownership, the lite/full choice, preload and prefetch, and the idle cost.

`install.mjs` is a stranger's website: the package is served from one origin and the page from another, and it checks every way of using it
(one script tag with no config, data attributes, `create()` by hand, nothing downloaded before the pointer moves, a strict CSP, the ES module).
The tests use Chrome through `playwright-core`; set `PLAYWRIGHT_DIR` if yours lives somewhere else.

## Feedback

Tried it? **[Rate it](https://github.com/Abhishakth007/Spider_Crawl_Cursor_Animation/issues/new?template=feedback.yml)**, or star the repo. I read everything.

## License

MIT, see [LICENSE](LICENSE).
