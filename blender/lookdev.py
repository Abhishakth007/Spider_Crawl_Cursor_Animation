"""Look-dev stills: build the spider, pose it, and render a few views.

    blender -b --factory-startup -P lookdev.py -- OUT_DIR [--views top,tq,face,side] [--res 900] [--samples 128]
                                                   [--phase 0] [--theta 0] [--elev 78] [--save spider.blend] [--floor]
"""
import sys, os, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector
import spider_model as M
import spider_motion as MO
import spider_render as R

argv = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(argv[0])
opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
res = int(opt("--res", "900"))
samples = int(opt("--samples", "128"))
views = opt("--views", "top,tq,face,side").split(",")
phase, theta = float(opt("--phase", "0")), float(opt("--theta", "0"))
elev = float(opt("--elev", "76"))
os.makedirs(out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
t0 = time.time()
sp = M.build()
print("BUILT in", round(time.time() - t0, 1), "s")
MO.apply_pose(sp, MO.gait_pose(phase, theta))
bpy.context.view_layer.update()
kind, cam = R.setup(res=res, samples=samples, elev=elev, ortho=330, floor="--floor" in argv, transparent="--floor" not in argv)
print("DEVICE", kind)
if "--save" in argv:
    bpy.ops.wm.save_as_mainfile(filepath=opt("--save", "spider.blend"), copy=True)

sc = bpy.context.scene
VIEWS = {  # name: (elevation, ortho scale, target, azimuth of the camera, 0 = behind, 180 = in front)
    "top": (elev, 340, (0, -2, 0), "front"),
    "tq": (38, 300, (0, -4, 18), 35),
    "face": (22, 90, (0, 22, 16), 180 - 25),
    "side": (4, 300, (0, -8, 30), 90),
    "face_top": (elev, 100, (0, 20, 8), "front"),
}
for v in views:
    e, ortho, tgt, az = VIEWS[v]
    cam.data.ortho_scale = ortho
    if az == "front":
        R.aim(cam, e, tgt)
    else:
        ee = math.radians(e)
        a = math.radians(az)
        t = Vector(tgt)
        off = Vector((900 * math.cos(ee) * math.sin(a), -900 * math.cos(ee) * math.cos(a), 900 * math.sin(ee)))
        cam.location = t + off
        d = (t - cam.location).normalized()
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    dt = R.render(os.path.join(out, f"{v}.png"))
    print("RENDER", v, round(dt, 1), "s")
