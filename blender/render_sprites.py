"""Render the sprite strips on the GPU (Cycles / OptiX), one PNG per frame.

    blender -b --factory-startup -P render_sprites.py -- OUT_DIR [--skin spidey|widow] [--res 768] [--samples 128]
        [--strips walk0,pivot,...] [--frames 0,5,9] [--elev 76] [--ortho 480] [--tm AgX] [--hair 1.0] [--save spider.blend] [--force]

OUT_DIR gets <strip>_<NN>.png (transparent, with the soft shadow baked into the alpha) and meta.json (what the page needs to place
and pace the sprite). Skips frames that already exist (use --force to redo), so a long render can be stopped and resumed.
"""
import sys, os, json, time, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bpy
import anatomy as A
import gait as G
import build as B
import pose as PS
import scene as S

argv = sys.argv[sys.argv.index("--") + 1:]
opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
out = os.path.abspath(argv[0]); os.makedirs(out, exist_ok=True)
skin = opt("--skin", "spidey")
res = int(opt("--res", "768")); samples = int(opt("--samples", "128"))
elev = float(opt("--elev", "76")); ortho = float(opt("--ortho", "400"))
strips = opt("--strips", ",".join(G.COUNTS)).split(",")
only = [int(v) for v in opt("--frames", "").split(",") if v != ""]
hair = float(opt("--hair", "1.0"))

bpy.ops.wm.read_factory_settings(use_empty=True)
t0 = time.time()
sp = B.build(skin, hair)
LIGHT = {"spidey": dict(key=2.8, rim=1.8, sky=0.15), "widow": dict(key=3.0, rim=3.4, sky=0.22)}[skin]
kind, cam, floor, lights = S.setup(res=res, samples=samples, elev=elev, ortho=ortho, target=(0.0, G.PIV_Y, 0.0), shadow=True,
                                   tonemap=opt("--tm", "AgX"), sky=float(opt("--sky", LIGHT["sky"])), key=float(opt("--key", LIGHT["key"])),
                                   fill=float(opt("--rim", LIGHT["rim"])), shadow_strength=float(opt("--shadow", "1.6")))
S.link_lights_to_spider(floor)
print("BUILT", round(time.time() - t0, 1), "s; device", kind, flush=True)
meta = {"frame_px": res, "frame_bu": ortho, "elev": elev, "pivot_bu": [0.0, round(G.PIV_Y, 3), 0.0],
        "stride_bu": A.STRIDE, "turn_deg": math.degrees(A.TURN), "beta": A.BETA,
        "counts": G.COUNTS, "walks": G.WALKS, "head_bu": round(A.HEAD_Y - G.PIV_Y, 2), "body_bu": A.BODY_BU,
        "span_bu": round(2 * max(abs(J["F"][0]) for J in G.pose(0, 0)["legs"].values()), 1), "skin": skin, "shadow": "baked"}
json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=1)
if "--save" in argv:
    PS.apply_pose(sp, G.pose(0, 0)); bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(opt("--save", "spider.blend")), copy=True)
total = sum(len(only) if only else G.COUNTS[s] for s in strips)
done = 0; t1 = time.time()
for name in strips:
    n = G.COUNTS[name]
    for k in (only if only else range(n)):
        if k >= n:
            continue
        path = os.path.join(out, f"{name}_{k:02d}.png")
        done += 1
        if os.path.exists(path) and "--force" not in argv:
            continue
        PS.apply_pose(sp, G.strip_pose(name, k))
        bpy.context.view_layer.update()
        dt = S.render(path)
        el = time.time() - t1
        print(f"FRAME {done}/{total} {name}_{k:02d} {dt:.1f}s  elapsed {el/60:.1f} min", flush=True)
print("DONE", round(time.time() - t0, 1), "s")
