"""Render the real model in the reference video's three views (top with the head down, side with the head to the right, front),
at the same phases (video frames of the 120-frame cycle), for laying next to the reference.

    blender -b --factory-startup -P compare_views.py -- OUT_DIR [--phases 0,20,40,...] [--theta 0] [--mode walk] [--samples 32]
"""
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bpy
from mathutils import Vector, Matrix
import anatomy as A
import gait as G
import build as B
import pose as PS
import scene as S

argv = sys.argv[sys.argv.index("--") + 1:]
opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
out = os.path.abspath(argv[0]); os.makedirs(out, exist_ok=True)
phases = [int(v) for v in opt("--phases", ",".join(str(20 * k) for k in range(6))).split(",")]
theta = float(opt("--theta", "0")); mode = opt("--mode", "walk"); samples = int(opt("--samples", "32"))
skin = opt("--skin", "spidey")

bpy.ops.wm.read_factory_settings(use_empty=True)
sp = B.build(skin, float(opt("--hair", "0.35")))
kind, cam, floor, lights = S.setup(res=640, samples=samples, shadow=True, tonemap="AgX", sky=0.25, key=2.8)
S.link_lights_to_spider(floor)
sc = bpy.context.scene
VIEWS = {
    "top": (640, 720, 330.0, (0, 0, 1), (0, -1, 0), (0, 4, 30)),
    "side": (1120, 320, 560.0, (1, 0, 0.0), (0, 0, 1), (0, -12, 56)),
    "front": (910, 400, 460.0, (0, 1, 0.22), (0, 0, 1), (0, 0, 62)),
}


def aim(name):
    w, h, scale, d, up, tgt = VIEWS[name]
    sc.render.resolution_x, sc.render.resolution_y = w, h
    cam.data.ortho_scale = scale
    d = Vector(d).normalized(); t = Vector(tgt)
    cam.location = t + d * 1200
    q = (-d).to_track_quat("-Z", "Y")
    cam_up = q @ Vector((0, 1, 0))
    ang = math.atan2(cam_up.cross(Vector(up)).dot(-d), cam_up.dot(Vector(up)))
    cam.rotation_euler = (Matrix.Rotation(ang, 3, -d) @ q.to_matrix()).to_euler()


for f in phases:
    ph = (f / 120.0) % 1.0
    P = G.pose(ph, theta) if mode == "walk" else G.idle_pose(mode, ph)
    PS.apply_pose(sp, P)
    bpy.context.view_layer.update()
    for name in VIEWS:
        aim(name)
        S.render(os.path.join(out, f"{name}_{f:03d}.png"))
print("DONE", len(phases))
