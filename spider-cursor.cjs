/*!
 * SpiderCursor: a spider that follows your cursor.   https://github.com/Abhishakth007/Spider_Crawl_Cursor_Animation
 *
 * The spider was modelled, furred and rendered in Blender (Cycles, on the GPU); this file only plays the frames back. It is
 * its own animal: the pointer stays the pointer, and the spider crawls after it, slowly, the way a spider does.
 *
 *   - It walks on eight legs in the two alternating tetrapods real spiders use, and the legs run exactly as fast as it
 *     goes, so planted feet do not skate. It turns the way a walking animal does, in an arc, with the body bending into it.
 *   - It does not chase the pointer onto its tip. It comes up behind it and stops a little short while you are moving.
 *   - If the pointer sits still, the spider walks the last of the way in and settles on it. While it sits there the
 *     system arrow is hidden (the spider is the cursor); the moment the pointer moves, the arrow comes back and the
 *     spider is a separate animal again.
 *   - Standing, it breathes, its palps twitch, and now and then it waves a front leg, taps a back one or grooms its fangs.
 *
 * Use it (any one of these):
 *
 *   <script src="https://cdn.jsdelivr.net/npm/spider-crawl-cursor"></script>              one line, nothing to host
 *   <script src="spider-cursor.js" data-size="40"></script>                                  your own copy of the folder
 *   <script src="spider-cursor.js"></script>
 *   <script>SpiderCursor.create({ size: 40 });</script>                                      or start it yourself
 *   import SpiderCursor from "spider-crawl-cursor";  SpiderCursor.create({ size: 40 });      with a bundler (sprites come from the CDN)
 *
 * The script starts itself when it is loaded with a <script> tag. If you call create() yourself it does not start twice;
 * add data-manual to switch the automatic start off (for example when you inject the script from your own code).
 *
 * Options (as create({...}) or, in a script tag, as data-size, data-speed ...)
 *   src        folder with the sprite sheets (assets/<size>/<strip>.webp)                     default: the assets/ folder next to
 *                                                                                              this script, or the CDN copy
 *   size       body length of the spider in CSS px, head to abdomen (the legs reach about 1.8x) default 34
 *   speed      1 is a slow crawl; 2 is twice as fast                                           default 1
 *   perch      hide the arrow while the spider sits on the pointer                             default true
 *   standoff   how far short of a moving pointer it stops, in body lengths                     default 0.7
 *   spawn      "edge": comes in from the nearest edge of the window (starting no further than    default "edge"
 *              about 7 body lengths from the pointer, so there is something to see at once); "pointer": starts on it
 *   fidget     now and then waves, taps or grooms while standing                               default true
 *   shadow     a soft drop shadow                                                              default true
 *   touch      also for touch input                                                            default false
 *   minWidth   do nothing on windows narrower than this many px                                default 0
 *   manifest   read manifest.json from src instead of the copy built into this file (only      default false
 *              needed if you repacked the sheets with other sizes)
 *   zIndex                                                                                     default 2147483647
 * Only one size of sprite is ever downloaded. A desktop browser fetches the two sheets it needs as soon as the page is idle,
 * so the spider is there the moment the mouse first moves; a phone (no mouse) downloads nothing at all.
 * Returns { destroy(), set(opts), setSize(px), show(), hide(), position(), state() }.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.SpiderCursor = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var VERSION = "1.0.1";                              // the build step puts the package version here
  // Where this script was loaded from, read now, while it is running. The sprites live in assets/ beside it, so a page that
  // loads it from anywhere (a CDN, another site, a sub-folder) finds them without being told. The bundler builds blank this.
  var SELF = "";
  var CDN = "https://cdn.jsdelivr.net/npm/spider-crawl-cursor" + (VERSION.charAt(0) === "_" ? "" : "@" + VERSION) + "/assets/";
  function defaultSrc() {
    if (!SELF) return CDN;
    var u = SELF.replace(/[#?].*$/, "");
    // .../spider-cursor.min.js -> its folder; a bare package URL (.../npm/spider-crawl-cursor@1) is the folder itself
    u = /\.[cm]?js$/i.test(u) ? u.replace(/[^\/]*$/, "") : u.replace(/\/?$/, "/");
    return u + "assets/";
  }
  var created = 0;

  // what the renders were made with (pack.py rewrites this from the Blender run); this copy is what the page uses unless it asks for manifest.json
  var META = /*META*/{"frame_px":768,"frame_bu":340.0,"elev":76.0,"pivot_bu":[0.0,-2.0,0.0],"stride_bu":84.0,"turn_deg":48.00000000000001,"beta":0.6,"counts":{"walk0":32,"walk18":32,"walk34":32,"walk50":32,"walk70":32,"pivot":32,"idle_calm":48,"idle_wave":60,"idle_tap":44,"idle_groom":52},"walks":{"walk0":0.0,"walk18":18.0,"walk34":34.0,"walk50":50.0,"walk70":70.0,"pivot":90.0},"head_bu":34.0,"body_bu":136.0,"span_bu":244.0,"cols":8,"tiers":[64,96,128,192,256],"format":"webp"}/*ENDMETA*/;
  var COLS = 8;
  var STRIP_STEP = [0, 18, 34, 50, 70, 90];               // the gait strips, by how sharply they turn: 0 walks straight, 90 pivots
  var STRIP_NAME = { 0: "walk0", 18: "walk18", 34: "walk34", 50: "walk50", 70: "walk70", 90: "pivot" };
  var ARC_MAX = 50;                                       // the sharpest turn it makes while it has room to walk (an arc about a body length across)
  var SPECIALS = ["idle_wave", "idle_tap", "idle_groom"];
  var FADE = 0.08;                                        // seconds to cross-fade when one strip hands over to another

  var TAU = Math.PI * 2;
  var wrap = function (a) { return Math.atan2(Math.sin(a), Math.cos(a)); };
  var clamp = function (v, a, b) { return v < a ? a : v > b ? b : v; };
  var rand = function (a, b) { return a + Math.random() * (b - a); };

  function create(opts) {
    opts = Object.assign({ src: defaultSrc(), size: 34, speed: 1, perch: true, standoff: 0.7, spawn: "edge", fidget: true, shadow: true,
                           touch: false, minWidth: 0, manifest: false, zIndex: 2147483647, debug: false }, opts || {});
    created++;
    if (typeof window === "undefined" || (opts.minWidth && window.innerWidth < opts.minWidth)) {
      var no = function () {};
      return { destroy: no, set: no, setSize: no, show: no, hide: no, position: function () { return { x: -1, y: -1, head: { x: -1, y: -1 } }; }, state: function () { return { ready: false }; } };
    }
    var reduce = typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
    var dead = false, shown = true;

    // ---- the canvas
    var cv = document.createElement("canvas");
    cv.setAttribute("aria-hidden", "true");
    var st = cv.style;
    st.position = "fixed"; st.left = "0"; st.top = "0"; st.pointerEvents = "none"; st.zIndex = String(opts.zIndex);
    st.willChange = "transform"; st.opacity = "0"; st.transition = "opacity .25s";
    if (opts.shadow) st.filter = "drop-shadow(0 .6px .6px rgba(36,24,10,.38)) drop-shadow(.8px 2.4px 2.2px rgba(36,24,10,.20))";
    var g = cv.getContext("2d");
    // hiding the arrow while the spider sits on it: a constructed stylesheet, which a strict Content-Security-Policy allows
    // (a <style> element it may not), with the element as the fallback for older browsers
    var PERCH_CSS = "html[data-spider-perched], html[data-spider-perched] * { cursor: none !important; }";
    var perchSheet = null, perchStyle = null;
    try { perchSheet = new CSSStyleSheet(); perchSheet.replaceSync(PERCH_CSS); document.adoptedStyleSheets = document.adoptedStyleSheets.concat(perchSheet); }
    catch (e) { perchSheet = null; perchStyle = document.createElement("style"); perchStyle.textContent = PERCH_CSS; document.head.appendChild(perchStyle); }
    document.body.appendChild(cv);

    // ---- what the renders were made with, and the sheets
    var M = null, tier = 0, sheets = {}, loading = {}, ready = false;
    var s = 1;                  // css px per Blender unit
    var frameCss = 0, dev = 0, dpr = 1;
    var D0 = 1, W0 = 1, HEAD = 0;

    function base() { return opts.src.replace(/\/?$/, "/"); }
    function pickTier() {
      var want = frameCss * dpr, best = 0;
      var t = M.tiers.slice().sort(function (a, b) { return a - b; });
      for (var i = 0; i < t.length; i++) if (t[i] >= want * 0.9) { best = t[i]; break; }
      return best || t[t.length - 1];
    }
    function loadStrip(name) {
      if (sheets[name] || loading[name]) return loading[name];
      var T = tier;
      loading[name] = new Promise(function (res) {
        var im = new Image();
        im.onload = function () { if (T === tier) sheets[name] = im; delete loading[name]; res(im); };
        im.onerror = function () { delete loading[name]; res(null); };
        im.src = base() + T + "/" + name + "." + M.format;
      });
      return loading[name];
    }
    function setSize(px) {
      opts.size = px;
      if (!M) return;
      dpr = Math.min(window.devicePixelRatio || 1, 3);
      s = px / M.body_bu;
      frameCss = M.frame_bu * s;
      dev = Math.max(2, Math.round(frameCss * dpr));
      cv.width = dev; cv.height = dev;
      st.width = frameCss + "px"; st.height = frameCss + "px";
      g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high";
      D0 = M.stride_bu * s;                              // body travel per cycle, walking straight
      W0 = M.turn_deg * Math.PI / 180;                   // body turn per cycle, pivoting
      HEAD = M.head_bu * Math.sin(M.elev * Math.PI / 180) * s;
      var t = pickTier();
      if (t !== tier) {
        tier = t; sheets = {}; loading = {}; ready = false;
        Promise.all([loadStrip("walk0"), loadStrip("idle_calm")]).then(function () { if (t === tier) { ready = true; dirty = true; } });
        if (spawned) loadRest();
      }
      dirty = true;
    }
    // the curves, the pivot and the fidgets are not needed until it has appeared and started to walk
    function loadRest() { ["walk18", "walk34", "walk50", "walk70", "pivot", "idle_wave", "idle_tap", "idle_groom"].forEach(loadStrip); }

    // ---- state. Positions are the spider's pivot (the middle of its feet); heading 0 faces up the screen, + is clockwise
    var X = -999, Y = -999, th = 0, v = 0, w = 0, phase = 0;
    var mode = "idle";                 // idle | gait | stopping
    var px = 0, py = 0, seen = false, lastMove = 0, anchorX = 0, anchorY = 0, perched = false, pressed = 0, pressT = 0;
    var inputOk = true, spawned = false, dirty = true, enterUntil = 0;
    var strip = "idle_calm", mirror = false, idleMirror = false, idleT = 0, idleStrip = "idle_calm", nextFidget = 0, turnSign = 1;
    var stripAngle = 0, lastKey = "", fade = null, lastSpec = null;
    var lastT = performance.now();

    function head() { return { x: X + Math.sin(th) * HEAD, y: Y - Math.cos(th) * HEAD }; }

    function spawn() {
      spawned = true;
      loadRest();
      var t0 = performance.now();
      if (opts.spawn === "pointer") { th = 0; X = px; Y = py + HEAD; mode = "idle"; perched = false; nextFidget = t0 + 3000; return; }
      var W = innerWidth, H = innerHeight, m = frameCss * 0.55;
      var d = [px, W - px, py, H - py], k = d.indexOf(Math.min.apply(null, d));
      if (k === 0) { X = -m; Y = clamp(py, 0, H); } else if (k === 1) { X = W + m; Y = clamp(py, 0, H); }
      else if (k === 2) { Y = -m; X = clamp(px, 0, W); } else { Y = H + m; X = clamp(px, 0, W); }
      // A slow crawl from the far edge of a big window is a long wait for a first look: start no further than about seven
      // body lengths from the pointer, along the same line. Nearer than that it still walks in from the edge; further, it
      // fades in there (the canvas fades in over a quarter of a second) and scuttles the rest, quicker than it crawls.
      var dx = X - px, dy = Y - py, dd = Math.hypot(dx, dy), reach = 7 * opts.size;
      if (dd > reach) { X = px + dx * reach / dd; Y = py + dy * reach / dd; }
      th = Math.atan2(px - X, -(py - Y));
      mode = "idle"; nextFidget = t0 + 3000; enterUntil = t0 + 4500;
    }

    function onMove(e) {
      if (!inputOk || (e.pointerType === "touch" && !opts.touch)) return;
      var now = performance.now();
      px = e.clientX; py = e.clientY;
      if (!seen) { seen = true; anchorX = px; anchorY = py; lastMove = now; boot(); if (M) { spawn(); st.opacity = "1"; } }
      if (Math.hypot(px - anchorX, py - anchorY) > 2.5) { anchorX = px; anchorY = py; lastMove = now; }
      if (perched && Math.hypot(px - perchX, py - perchY) > 2.5) setPerched(false);
    }
    var perchX = 0, perchY = 0;
    function setPerched(on) {
      if (on === perched) return;
      perched = on;
      if (on) { perchX = px; perchY = py; }
      if (opts.perch) { if (on) document.documentElement.setAttribute("data-spider-perched", ""); else document.documentElement.removeAttribute("data-spider-perched"); }
    }
    function onDown() { pressed = 1; pressT = performance.now(); dirty = true; }
    function onUp() { pressed = 0; dirty = true; }
    var opt = { passive: true, capture: true };
    window.addEventListener("pointermove", onMove, opt);
    window.addEventListener("pointerdown", onDown, opt);
    window.addEventListener("pointerup", onUp, opt);

    // ---- one tick of the spider
    var F_CRUISE = 3.0, A_UP = 320, A_DOWN = 520, A_TURN = 8, MIN_F = 0.85;
    var DEG = Math.PI / 180;
    function step(dt, now) {
      var hd = head(), dxp = px - hd.x, dyp = py - hd.y, dist = Math.hypot(dxp, dyp);
      // steer from the pivot, not from the head: turning on the spot moves the head round a circle, and a target inside that
      // circle (a pointer jiggled a few pixels) would be chased for ever. A pointer under the body counts as arrived.
      var bx = px - X, by = py - Y, under = Math.hypot(bx, by) < HEAD * 0.95;
      var active = now - lastMove < 650;
      var E = active ? opts.standoff * opts.size : 0;
      if (enterUntil && dist < 3 * opts.size) enterUntil = 0;           // the scuttle in is over the first time it gets near the pointer
      var speedK = opts.speed * (reduce ? 0.6 : 1) * (!reduce && now < enterUntil ? 1.6 : 1);   // a quick scuttle in, then the crawl
      var goal = !under && dist > (active ? E + 2 : 3.5);
      var vd = 0, wd = 0, e = 0;
      if (goal && spawned) {
        var rem = dist - E;
        e = wrap(Math.atan2(bx, -by) - th);
        var ae = Math.abs(e);
        // How sharply to turn follows how far off it is pointing: gently for a small error, and never sharper than an arc
        // while there is room for one, so even a 180 is a swing round with the legs still carrying it forward, not a spin
        // on the spot. Only when the pointer is too close for an arc does it shuffle round on the spot.
        var arcR = D0 * Math.cos(ARC_MAX * DEG) / (W0 * Math.sin(ARC_MAX * DEG));
        var tight = dist < 2.2 * arcR && ae > 0.5;
        var want = Math.min(tight ? 90 : ARC_MAX, Math.asin(Math.min(1, 1.3 * ae)) / DEG);
        var cur = mode === "idle" ? 0 : stripAngle, q = 0, bd = 1e9;      // the nearest strip, sticking to the current one a little
        for (var i = 0; i < STRIP_STEP.length; i++) { var dd = Math.abs(want - STRIP_STEP[i]) - (STRIP_STEP[i] === cur ? 9 : 0); if (dd < bd) { bd = dd; q = STRIP_STEP[i]; } }
        stripAngle = q;
        if (q > 0) turnSign = Math.sign(e) || turnSign;
        var fcmd = F_CRUISE * speedK * (1 + 0.3 * clamp((dist - 4 * opts.size) / (14 * opts.size), 0, 1)) * (1 - 0.3 * q / 90);
        var cq = q === 90 ? 0 : Math.cos(q * DEG);
        var vnom = fcmd * D0 * cq, vlim = Math.sqrt(2 * 240 * Math.max(rem, 0)) + 0.8 * D0 * MIN_F;
        if (vnom > vlim) fcmd *= Math.max(0.35, vlim / vnom);              // ease off on the way in: the whole gait slows together
        if (rem > 3) fcmd = Math.max(fcmd, MIN_F);
        vd = fcmd * D0 * cq;
        wd = q > 0 ? Math.sign(e) * fcmd * W0 * Math.sin(q * DEG) : clamp(2.0 * e, -0.35, 0.35);
      }

      // the legs can only change so fast
      var av = vd > v ? A_UP : A_DOWN;
      v += clamp(vd - v, -av * dt, av * dt);
      w += clamp(wd - w, -A_TURN * dt, A_TURN * dt);
      if (Math.abs(v) < 0.01 && vd === 0) v = 0;
      if (Math.abs(w) < 0.002 && wd === 0) w = 0;
      // a body turns in steps: the yaw is quickest mid-stride and eases at the moment all eight feet are down
      var cad = (mode !== "idle" && stripAngle > 0) ? 1 - 0.3 * Math.sin(stripAngle * DEG) * Math.cos(4 * Math.PI * phase) : 1;
      th = wrap(th + w * dt * cad);
      X += Math.sin(th) * v * dt; Y -= Math.cos(th) * v * dt;

      // ---- the gait: from the speed and the turn, the strip and the rate the legs must run at
      var fl = Math.hypot(v / D0, w / W0);
      var wantMove = vd > 0 || wd !== 0;
      if (mode === "idle" && wantMove) { mode = "gait"; phase = idleMirror ? 0.5 : 0; idleT = 0; fade = null; }
      else if (mode === "gait" && !wantMove && v < 0.35 * D0 && Math.abs(w) < 0.35 * W0) { mode = "stopping"; }
      else if (mode === "stopping" && wantMove) mode = "gait";
      if (mode === "gait" || mode === "stopping") {
        var fr = mode === "stopping" ? Math.max(fl, 1.1) : Math.max(fl, MIN_F * 0.8);
        var ph0 = phase;
        phase += fr * dt;
        if (mode === "stopping" && Math.floor(phase * 2) !== Math.floor(ph0 * 2)) {   // double support: all eight feet down
          phase = Math.floor(phase * 2) / 2; idleMirror = Math.round(phase * 2) % 2 === 1; mode = "idle"; idleT = 0; idleStrip = "idle_calm"; nextFidget = now + rand(2500, 6000); stripAngle = 0;
        }
        phase -= Math.floor(phase);
        if (mode !== "idle") { strip = STRIP_NAME[stripAngle]; mirror = stripAngle > 0 && turnSign > 0; }
      }
      // ---- standing: breathe, and now and then do something
      if (mode === "idle") {
        strip = idleStrip; mirror = idleMirror;
        var count = M.counts[idleStrip];
        idleT += dt * 24;
        if (idleT >= count) {
          idleT -= count;
          if (idleStrip !== "idle_calm") { idleStrip = "idle_calm"; nextFidget = now + rand(3500, 9000); }
          else if (opts.fidget && !reduce && now > nextFidget && sheets[SPECIALS[0]]) {
            idleStrip = SPECIALS[Math.floor(Math.random() * SPECIALS.length)];
            if (!sheets[idleStrip]) idleStrip = "idle_calm";
          }
          strip = idleStrip;
        }
      }

      // ---- arrived: settle on the pointer
      if (mode === "idle" && !active && (dist < 5 || under) && !perched) setPerched(true);
      if (mode !== "idle" && perched && Math.hypot(px - perchX, py - perchY) > 2.5) setPerched(false);
    }

    // ---- drawing
    function spec() {
      var n = M.counts[strip], i;
      if (mode === "idle") i = Math.min(n - 1, Math.floor(idleT));
      else { var ph = phase + (mirror ? 0.5 : 0); i = Math.floor((ph - Math.floor(ph)) * n) % n; }
      return { strip: strip, i: i, mirror: mirror };
    }
    function blit(sp, alpha) {
      var im = sheets[sp.strip] || sheets.walk0 || sheets.idle_calm;
      if (!im) return;
      var T = tier, i = sp.i;
      g.save();
      g.translate(dev / 2 + offX, dev / 2 + offY);
      g.rotate(th);
      if (sp.mirror) g.scale(-1, 1);
      var sc = 1 - 0.08 * pressedAmt;
      g.scale(sc, sc);
      g.globalAlpha = alpha;
      g.drawImage(im, (i % COLS) * T, Math.floor(i / COLS) * T, T, T, -dev / 2, -dev / 2, dev, dev);
      g.restore();
    }
    var pressedAmt = 0, offX = 0, offY = 0;
    function draw(dt) {
      var sp = spec();
      pressedAmt += ((pressed ? 1 : 0) - pressedAmt) * Math.min(1, dt * 18);
      if (lastSpec && (lastSpec.strip !== sp.strip || lastSpec.mirror !== sp.mirror)) fade = { from: lastSpec, t: 0 };
      lastSpec = sp;
      if (fade) { fade.t += dt / FADE; if (fade.t >= 1) fade = null; }
      // the canvas sits on whole device pixels (so the compositor never resamples it); the part of a pixel is drawn inside
      var gx = (X - frameCss / 2) * dpr, gy = (Y - frameCss / 2) * dpr, ix = Math.floor(gx), iy = Math.floor(gy);
      offX = gx - ix; offY = gy - iy;
      cv.style.transform = "translate3d(" + (ix / dpr) + "px," + (iy / dpr) + "px,0)";
      var key = sp.strip + sp.i + sp.mirror + th.toFixed(3) + pressedAmt.toFixed(2) + offX.toFixed(2) + offY.toFixed(2) + (fade ? "f" + fade.t.toFixed(2) : "");
      if (key === lastKey && !dirty) return;
      lastKey = key; dirty = false;
      g.setTransform(1, 0, 0, 1, 0, 0);
      g.globalCompositeOperation = "source-over";
      g.clearRect(0, 0, dev, dev);
      if (fade) {
        g.globalCompositeOperation = "lighter";
        blit(fade.from, 1 - fade.t); blit(sp, fade.t);
        g.globalCompositeOperation = "source-over";
      } else blit(sp, 1);
    }

    var raf = 0;
    function frame(now) {
      raf = requestAnimationFrame(frame);
      var dt = Math.min((now - lastT) / 1000, 0.05); lastT = now;
      if (!ready || !seen || !shown) return;
      if (!spawned) { spawn(); st.opacity = "1"; }
      step(dt, now);
      draw(dt);
      if (opts.debug) window.__spider = api.state();
    }

    // ---- start. The two sheets it needs are fetched as soon as the page is idle on a machine with a mouse (so the spider is
    // there the moment the mouse first moves); a phone, or any page nobody touches with a mouse, downloads nothing.
    var onResize = function () { setSize(opts.size); };
    var prepared = false, booted = false;
    function prepare() {
      if (prepared || dead) return;
      prepared = true;
      window.addEventListener("resize", onResize);
      var metaP = opts.manifest && typeof fetch === "function" && location.protocol !== "file:"
        ? fetch(base() + "manifest.json").then(function (r) { if (!r.ok) throw 0; return r.json(); }).catch(function () { return META; })
        : Promise.resolve(META);
      metaP.then(function (m) {
        if (dead) return;
        M = m; setSize(opts.size);
        if (seen && !spawned) { spawn(); st.opacity = "1"; }
      }).catch(function (err) { console.error("spider-cursor:", err); });
    }
    function boot() {
      prepare();
      if (booted || dead) return;
      booted = true;
      lastT = performance.now();
      raf = requestAnimationFrame(frame);
    }
    if (typeof matchMedia === "function" && matchMedia("(hover: hover) and (pointer: fine)").matches) {
      (window.requestIdleCallback || function (f) { return setTimeout(f, 250); })(prepare, { timeout: 2500 });
    }

    var api = {
      destroy: function () {
        dead = true; cancelAnimationFrame(raf);
        window.removeEventListener("pointermove", onMove, opt); window.removeEventListener("pointerdown", onDown, opt);
        window.removeEventListener("pointerup", onUp, opt); window.removeEventListener("resize", onResize);
        document.documentElement.removeAttribute("data-spider-perched");
        cv.remove();
        if (perchStyle) perchStyle.remove();
        if (perchSheet) document.adoptedStyleSheets = document.adoptedStyleSheets.filter(function (x) { return x !== perchSheet; });
      },
      setSize: setSize,
      set: function (o) { if (o.size) setSize(o.size); Object.keys(o).forEach(function (k) { if (k !== "size") opts[k] = o[k]; }); },
      show: function () { shown = true; inputOk = true; if (seen) st.opacity = "1"; },
      hide: function () { shown = false; inputOk = false; st.opacity = "0"; setPerched(false); },
      position: function () { return { x: X, y: Y, head: head() }; },
      state: function () { return { x: X, y: Y, heading: th, v: v, w: w, mode: mode, strip: strip, mirror: mirror, phase: phase, perched: perched, tier: tier, ready: ready, idle: idleStrip, stripAngle: stripAngle, frame: lastSpec && lastSpec.i }; },
    };
    return api;
  }

  // Loaded with a <script> tag, it starts itself once the page is parsed, unless the page has called create() by then
  // (so the explicit form below it is still fine) or the tag says data-manual / data-auto="false".
  function fromTag(el) {
    var d = el.dataset, o = {};
    if (d.src) o.src = d.src;
    if (d.spawn) o.spawn = d.spawn;
    ["size", "speed", "standoff", "minWidth", "zIndex"].forEach(function (k) { if (d[k] !== undefined && d[k] !== "" && !isNaN(+d[k])) o[k] = +d[k]; });
    ["perch", "fidget", "shadow", "touch", "manifest"].forEach(function (k) { if (d[k] !== undefined) o[k] = d[k] !== "false" && d[k] !== "0"; });
    return o;
  }
  var cs = typeof document !== "undefined" && document.currentScript;
  if (cs && cs.dataset && cs.dataset.manual === undefined && cs.dataset.auto !== "false") {
    var go = function () { if (!created) create(fromTag(cs)); };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go); else setTimeout(go, 0);
  }
  return { create: create, version: VERSION };
});
