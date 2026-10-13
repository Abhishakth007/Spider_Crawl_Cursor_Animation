"""Look-dev stills.

    blender -b --factory-startup -P lookdev.py -- OUT_DIR [--skin spidey|widow] [--views top,tq,face,side,back]
        [--res 900] [--samples 128] [--phase 0] [--theta 0] [--hair 1.0] [--floor] [--save spider.blend]
"""
import sys, os, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bpy
from mathutils import Vector
import anatomy as A
import gait as G
import build as B
import pose as PS
import scene as S

argv = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(argv[0])
opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
res = int(opt("--res", "900")); samples = int(opt("--samples", "128"))
views = opt("--views", "top,tq,face,side").split(",")
skin = opt("--skin", "spidey"); hair = float(opt("--hair", "1.0"))
phase, theta = float(opt("--phase", "0")), float(opt("--theta", "0"))
tag = opt("--tag", skin)
os.makedirs(out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
t0 = time.time()
sp = B.build(skin, hair)
print("BUILT in", round(time.time() - t0, 1), "s")
P = G.pose(phase, theta) if opt("--mode", "walk") == "walk" else G.idle_pose(opt("--mode", "walk"), phase)
PS.apply_pose(sp, P)
bpy.context.view_layer.update()
kind, cam, floor, lights = S.setup(res=res, samples=samples, elev=76.0, ortho=480.0, shadow="--floor" in argv or "--shadow" in argv,
                                   transparent="--bg" not in argv, tonemap=opt("--tm", "Standard"), sky=float(opt("--sky", "0.30")), key=float(opt("--key", "3.2")),
                                   fill=float(opt("--rim", "1.8")))
if floor is not None:
    S.link_lights_to_spider(floor)
print("DEVICE", kind)
if "--save" in argv:
    bpy.ops.wm.save_as_mainfile(filepath=opt("--save", "spider.blend"), copy=True)

VIEWS = {  # name: (elevation, ortho scale, target, azimuth (None = the sprite camera))
    "top": (76, 480, (0, 12, 0), None),
    "hero": (76, 330, (0, 6, 0), None),
    "topclose": (76, 250, (0, -6, 20), None),
    "tq": (34, 340, (0, -10, 40), 35),
    "tq2": (30, 340, (0, -10, 40), 215),
    "face": (20, 70, (0, 28, 40), 180 - 20),
    "head": (60, 96, (0, 18, 44), 180),
    "side": (4, 380, (0, -8, 52), 90),
    "back": (50, 300, (0, -55, 32), 0),
}
for v in views:
    e, ortho, tgt, az = VIEWS[v]
    if az is None:
        S.aim(cam, e, tgt); cam.data.ortho_scale = ortho
    else:
        S.aim_view(cam, e, az, tgt, ortho)
    dt = S.render(os.path.join(out, f"{tag}_{v}.png"))
    print("RENDER", v, round(dt, 1), "s", flush=True)
