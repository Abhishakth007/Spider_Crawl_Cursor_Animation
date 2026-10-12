"""Render the sprite strips on the GPU (Cycles / OptiX), one PNG per frame.

    blender -b --factory-startup -P render_sprites.py -- OUT_DIR [--res 512] [--samples 96] [--strips walk0,pivot,...]
                                                          [--frames 0,5,9] [--elev 80] [--ortho 340] [--denoiser OPTIX]
                                                          [--save spider.blend] [--cpu]

OUT_DIR gets <strip>_<NN>.png (transparent) and meta.json (what the page needs to place and pace the sprite).
Skips frames that already exist (use --force to redo), so a long render can be stopped and resumed.
"""
import sys, os, json, time, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bpy
import spider_model as M, spider_motion as MO, spider_render as R

argv = sys.argv[sys.argv.index("--") + 1:]
opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
out = os.path.abspath(argv[0]); os.makedirs(out, exist_ok=True)
res = int(opt("--res", "512")); samples = int(opt("--samples", "96"))
elev = float(opt("--elev", "80")); ortho = float(opt("--ortho", "340"))
strips = opt("--strips", ",".join(MO.COUNTS)).split(",")
only = [int(v) for v in opt("--frames", "").split(",") if v != ""]
PIVOT = (0.0, -2.0, 0.0)

bpy.ops.wm.read_factory_settings(use_empty=True)
t0 = time.time()
sp = M.build()
kind, cam = R.setup(res=res, samples=samples, elev=elev, ortho=ortho, target=PIVOT, denoiser=opt("--denoiser", "OPENIMAGEDENOISE"))
print("BUILT", round(time.time() - t0, 1), "s; device", kind)
meta = {"frame_px": res, "frame_bu": ortho, "elev": elev, "pivot_bu": list(PIVOT),
        "stride_bu": MO.STRIDE, "turn_deg": math.degrees(MO.TURN), "beta": MO.BETA,
        "counts": MO.COUNTS, "walks": MO.WALKS, "head_bu": 34.0, "body_bu": 136.0, "span_bu": 244.0}
json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=1)
if "--save" in argv:
    MO.apply_pose(sp, MO.gait_pose(0, 0)); bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(opt("--save", "spider.blend")), copy=True)
total = sum(len(only) if only else MO.COUNTS[s] for s in strips)
done = 0; t1 = time.time()
for name in strips:
    n = MO.COUNTS[name]
    for k in (only if only else range(n)):
        if k >= n:
            continue
        path = os.path.join(out, f"{name}_{k:02d}.png")
        done += 1
        if os.path.exists(path) and "--force" not in argv:
            continue
        MO.apply_pose(sp, MO.strip_pose(name, k))
        bpy.context.view_layer.update()
        dt = R.render(path)
        el = time.time() - t1
        print(f"FRAME {done}/{total} {name}_{k:02d} {dt:.1f}s  elapsed {el/60:.1f} min", flush=True)
print("DONE", round(time.time() - t0, 1), "s")
