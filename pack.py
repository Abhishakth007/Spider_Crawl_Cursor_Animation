"""Pack the Blender renders into sprite sheets for the page, one set per size.

    python pack.py renders/master assets [--profile full|lite] [--tiers 64,96,128,192,256]

For every strip (walk0, pivot, idle_calm ...) and every tier (frame size in pixels) this writes assets/<tier>/<strip>.webp,
a grid of frames, 8 to a row, plus assets/manifest.json (what the renders were made with, so the page can place and pace them).

Why tiers: a sprite that is shrunk in the browser is shrunk with a cheap filter, and thin legs and fur turn to mush. So each
size is made here, once, properly: premultiplied (so the edge does not pick up a dark halo), Lanczos from the 768 px master,
then a little sharpening on the colour, and the page picks the tier closest to the pixels it needs.
"""
import argparse, sys, os, json
import numpy as np
from PIL import Image, ImageFilter

COLS = 8


def arguments():
    parser = argparse.ArgumentParser(description="Build SpiderCursor sprite sheets")
    parser.add_argument("src")
    parser.add_argument("dst")
    parser.add_argument("--profile", choices=("full", "lite"), default="full")
    parser.add_argument("--tiers")
    parser.add_argument("--only", help="re-encode just these strips (comma separated); the manifest still describes them all")
    return parser.parse_args()


def strips_for(meta, profile):
    # Standing still shows one frame (the rest pose); all the movement of a standing spider is in the fidget strips. So idle_calm is that one
    # frame: a 48-frame strip would be about half of what a first visit downloads, and a third of what is decoded, to show a single picture.
    if profile == "full":
        strips = {name: (name, list(range(count))) for name, count in meta["counts"].items()}
        strips["idle_calm"] = ("idle_calm", [0])
        return strips
    # Lite retains the same start/end gait poses while sampling fewer intermediate frames.
    return {
        "walk0": ("walk0", list(range(0, meta["counts"]["walk0"], 2))),
        "walk34": ("walk34", list(range(0, meta["counts"]["walk34"], 2))),
        "pivot": ("pivot", list(range(0, meta["counts"]["pivot"], 2))),
        "idle_calm": ("idle_calm", [0]),
        "idle_still": ("idle_calm", [0]),
    }


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
    args = arguments()
    src, dst = args.src, args.dst
    with open(os.path.join(src, "meta.json"), encoding="utf-8") as handle:
        meta = json.load(handle)
    tiers = [int(v) for v in (args.tiers or ("64,96,128" if args.profile == "lite" else "64,96,128,192,256")).split(",")]
    strips = strips_for(meta, args.profile)
    only = set(args.only.split(",")) if args.only else None
    os.makedirs(dst, exist_ok=True)
    total = 0
    for px in tiers:
        d = os.path.join(dst, str(px))
        os.makedirs(d, exist_ok=True)
        tsum = 0
        for name, (source_name, frames) in strips.items():
            if only and name not in only:
                continue
            n = len(frames)
            rows = (n + COLS - 1) // COLS
            sheet = Image.new("RGBA", (min(COLS, n) * px, rows * px), (0, 0, 0, 0))      # a short strip is only as wide as it is long
            for k, frame in enumerate(frames):
                f = os.path.join(src, f"{source_name}_{frame:02d}.png")
                sheet.paste(shrink(f, px), ((k % COLS) * px, (k // COLS) * px))
            out = os.path.join(d, f"{name}.webp")
            q = (82 if args.profile == "lite" else 88) if px <= 128 else 84
            sheet.save(out, "WEBP", quality=q, method=6, alpha_quality=100, exact=True)
            tsum += os.path.getsize(out)
        print(f"tier {px}: {tsum/1e6:.2f} MB")
        total += tsum
    m = dict(meta)
    m["counts"] = {name: len(frames) for name, (_, frames) in strips.items()}
    m["walks"] = {name: meta["walks"][name] for name in meta["walks"] if name in strips}      # each profile lists the gait strips it really has
    m.update({"cols": COLS, "tiers": tiers, "format": "webp", "profile": args.profile})
    with open(os.path.join(dst, "manifest.json"), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(m, handle, indent=1)
        handle.write("\n")
    # keep the copy inside spider-cursor.js in step, for pages opened without a server
    js = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "spider-cursor.js")
    if os.path.exists(js):
        import re
        with open(js, encoding="utf-8") as handle:
            t = handle.read()
        marker = "LITEMETA" if args.profile == "lite" else "META"
        t = re.sub(r"/\*" + marker + r"\*/.*?/\*END" + marker + r"\*/", lambda _: "/*" + marker + "*/" + json.dumps(m, separators=(",", ":")) + "/*END" + marker + "*/", t, flags=re.S)
        with open(js, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(t)
    print(f"total {total/1e6:.2f} MB")


main()
