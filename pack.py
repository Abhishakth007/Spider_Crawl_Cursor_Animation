"""Pack the Blender renders into sprite sheets for the page, one set per size.

    python pack.py renders/master assets [--tiers 64,96,128,192,256]

For every strip (walk0, pivot, idle_calm ...) and every tier (frame size in pixels) this writes assets/<tier>/<strip>.webp,
a grid of frames, 8 to a row, plus assets/manifest.json (what the renders were made with, so the page can place and pace them).

Why tiers: a sprite that is shrunk in the browser is shrunk with a cheap filter, and thin legs and fur turn to mush. So each
size is made here, once, properly: premultiplied (so the edge does not pick up a dark halo), Lanczos from the 768 px master,
then a little sharpening on the colour, and the page picks the tier closest to the pixels it needs.
"""
import sys, os, json, glob
import numpy as np
from PIL import Image, ImageFilter

COLS = 8
src, dst = sys.argv[1], sys.argv[2]
tiers = [int(v) for v in (sys.argv[sys.argv.index("--tiers") + 1] if "--tiers" in sys.argv else "64,96,128,192,256").split(",")]
meta = json.load(open(os.path.join(src, "meta.json")))
counts = meta["counts"]


def shrink(path, px):
    im = Image.open(path).convert("RGBA")
    if px == im.width:
        return im
    pm = im.convert("RGBa")
    # half steps while far above the target keep Lanczos honest on the thin fur
    while pm.width > px * 2:
        pm = pm.resize((pm.width // 2, pm.height // 2), Image.LANCZOS)
    pm = pm.resize((px, px), Image.LANCZOS)
    out = pm.convert("RGBA")
    # unsharp on colour only; the strength falls as the frame gets bigger (the master needs none)
    amt = {64: 90, 96: 80, 128: 65, 160: 55, 192: 45, 256: 35, 384: 25}.get(px, 40)
    rgb = out.convert("RGB").filter(ImageFilter.UnsharpMask(radius=0.9 if px < 200 else 1.2, percent=amt, threshold=2))
    a = out.getchannel("A")
    res = rgb.convert("RGBA")
    res.putalpha(a)
    return res


def main():
    os.makedirs(dst, exist_ok=True)
    total = 0
    for px in tiers:
        d = os.path.join(dst, str(px))
        os.makedirs(d, exist_ok=True)
        tsum = 0
        for name, n in counts.items():
            rows = (n + COLS - 1) // COLS
            sheet = Image.new("RGBA", (COLS * px, rows * px), (0, 0, 0, 0))
            for k in range(n):
                f = os.path.join(src, f"{name}_{k:02d}.png")
                sheet.paste(shrink(f, px), ((k % COLS) * px, (k // COLS) * px))
            out = os.path.join(d, f"{name}.webp")
            q = 88 if px <= 128 else 84
            sheet.save(out, "WEBP", quality=q, method=6, alpha_quality=100, exact=True)
            tsum += os.path.getsize(out)
        print(f"tier {px}: {tsum/1e6:.2f} MB")
        total += tsum
    m = dict(meta)
    m.update({"cols": COLS, "tiers": tiers, "format": "webp"})
    json.dump(m, open(os.path.join(dst, "manifest.json"), "w"), indent=1)
    # keep the copy inside spider-cursor.js in step, for pages opened without a server
    js = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "spider-cursor.js")
    if os.path.exists(js):
        import re
        t = open(js, encoding="utf-8").read()
        t = re.sub(r"/\*META\*/.*?/\*ENDMETA\*/", lambda _: "/*META*/" + json.dumps(m, separators=(",", ":")) + "/*ENDMETA*/", t, flags=re.S)
        open(js, "w", encoding="utf-8").write(t)
    print(f"total {total/1e6:.2f} MB")


main()
