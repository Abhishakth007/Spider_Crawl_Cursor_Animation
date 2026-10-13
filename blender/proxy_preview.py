"""Stick-and-ellipsoid proxy of the spider, rendered in the reference video's three views (top with the head down, side with the
head to the right, front) so the gait can be laid next to the reference frame by frame.

    blender -b --factory-startup -P proxy_preview.py -- OUT_DIR [--phases 0,10,20,...] [--theta 0] [--mode walk]

Phases are in video frames of the 120-frame reference cycle (phase = frame / 120).
"""
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
import anatomy as A
import gait as G

argv = sys.argv[sys.argv.index("--") + 1:]
opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
out = os.path.abspath(argv[0]); os.makedirs(out, exist_ok=True)
phases = [int(v) for v in opt("--phases", ",".join(str(10 * k) for k in range(12))).split(",")]
theta = float(opt("--theta", "0"))
mode = opt("--mode", "walk")
frame_total = float(opt("--cycle", "120"))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"; sh.color_type = "OBJECT"; sh.show_shadows = True; sh.shadow_intensity = 0.35
sh.background_type = "WORLD"
sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.80, 0.75, 0.66)
sc.render.resolution_percentage = 100
sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"
try:
    sc.display.render_aa = "FXAA"
except Exception:
    pass


def unit_cyl(name):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=12, radius1=1.0, radius2=1.0, depth=1.0)
    for v in bm.verts:
        v.co.y, v.co.z = v.co.z + 0.5, v.co.y   # axis -> +Y, from 0 to 1
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return me


def unit_sphere(name):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=1.0)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


CYL, SPH = unit_cyl("cyl"), unit_sphere("sph")


def mk(name, mesh, color):
    ob = bpy.data.objects.new(name, mesh)
    sc.collection.objects.link(ob)
    ob.color = color
    return ob


BLACK, ORANGE, RED = (0.03, 0.03, 0.035, 1), (0.9, 0.32, 0.07, 1), (0.8, 0.12, 0.04, 1)
RAD = {"fem": 3.9, "pat": 3.5, "tib": 3.0, "met": 2.1, "tar": 1.5}
COL = {"fem": BLACK, "pat": ORANGE, "tib": ORANGE, "met": BLACK, "tar": BLACK}
segs = {}
for side in (-1, 1):
    for i in (1, 2, 3, 4):
        for name in RAD:
            segs[(side, i, name)] = mk(f"{name}{i}{side}", CYL, COL[name])
ct = mk("ct", SPH, (0.1, 0.1, 0.11, 1)); ab = mk("ab", SPH, RED)
CT_R = Vector((17.0, 27.0, 12.0)); AB_R = Vector((26.0, 40.0, 27.0))


def place_seg(ob, P0, P1, r):
    d = Vector(P1 - P0)
    L = d.length
    y = d.normalized()
    x = y.cross(Vector((0, 0, 1)))
    if x.length < 1e-4:
        x = Vector((1, 0, 0))
    x.normalize()
    z = x.cross(y)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(P0)
    ob.matrix_world = m @ Matrix.Diagonal((r, L, r, 1.0))


def apply(P):
    M = Matrix(P["ct"].tolist())
    ct.matrix_world = M @ Matrix.Translation((0, 2, 0)) @ Matrix.Diagonal((*CT_R, 1.0))
    st = P["body"]
    abm = M @ Matrix.Translation((0, -24, -2)) @ Matrix.Rotation(math.radians(14) + st["ab_pitch"], 4, "X") @ Matrix.Rotation(st["ab_yaw"], 4, "Z")
    ab.matrix_world = abm @ Matrix.Translation((0, -AB_R.y * 0.85, 0)) @ Matrix.Diagonal((*AB_R, 1.0))
    for (side, i), J in P["legs"].items():
        for name, (a, b) in (("fem", ("H", "K1")), ("pat", ("K1", "K2")), ("tib", ("K2", "A")), ("met", ("A", "M")), ("tar", ("M", "F"))):
            place_seg(segs[(side, i, name)], J[a], J[b], RAD[name])


# floor
me = bpy.data.meshes.new("floor"); me.from_pydata([(-900, -900, -0.2), (900, -900, -0.2), (900, 900, -0.2), (-900, 900, -0.2)], [], [(0, 1, 2, 3)])
fl = bpy.data.objects.new("floor", me); sc.collection.objects.link(fl); fl.color = (0.84, 0.79, 0.70, 1)

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
cam.data.type = "ORTHO"; cam.data.clip_start, cam.data.clip_end = 1, 5000; sc.camera = cam
VIEWS = {
    # name: (width, height, ortho scale across the width, camera direction from the target, up vector, target)
    "top": (640, 720, 330.0, (0, 0, 1), (0, -1, 0), (0, 10, 40)),
    "side": (1120, 320, 560.0, (1, 0, 0.0), (0, 0, 1), (0, -12, 62)),
    "front": (910, 400, 460.0, (0, 1, 0.22), (0, 0, 1), (0, 0, 70)),
}


def aim(name):
    w, h, scale, d, up, tgt = VIEWS[name]
    sc.render.resolution_x, sc.render.resolution_y = w, h
    cam.data.ortho_scale = scale
    d = Vector(d).normalized(); t = Vector(tgt)
    cam.location = t + d * 1200
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    q = (-d).to_track_quat("-Z", "Y")
    # roll so that `up` is the top of the image
    upv = Vector(up)
    cam_up = q @ Vector((0, 1, 0))
    ang = math.atan2(cam_up.cross(upv).dot(-d), cam_up.dot(upv))
    cam.rotation_euler = (Matrix.Rotation(ang, 3, -d) @ q.to_matrix()).to_euler()


def phase_pose(f):
    ph = (f / frame_total) % 1.0
    if mode == "walk":
        return G.pose(ph, theta)
    return G.idle_pose(mode, ph)


for f in phases:
    apply(phase_pose(f))
    bpy.context.view_layer.update()
    for name in VIEWS:
        aim(name)
        sc.render.filepath = os.path.join(out, f"{name}_{f:03d}.png")
        bpy.ops.render.render(write_still=True)
print("DONE", len(phases))
