"""Build the spider in Blender. build(skin) -> a Spider whose parts pose.apply() moves.

Everything rigid is its own object (a leg is five), and everything furry is a Curves object parented to the part it grows from,
so a part carries its fur with it. All dimensions come from anatomy.py.
"""
import math, random
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import anatomy as A
import bl_util as U
import materials as MT
from bl_util import pchip, add_obj, make_hair, surface_points, surface_area, mirror_x


class Spider:
    pass


# ------------------------------------------------------------------------------------------------ the carapace
CT_Y = [-27.0, -23.0, -17.0, -9.0, -1.0, 7.0, 15.0, 21.5, 26.5, 30.5, 33.5]
CT_W = [w * 1.08 for w in [4.0, 9.5, 15.5, 19.0, 20.4, 20.2, 18.8, 16.4, 12.8, 8.4, 3.2]]
CT_ZT = [z * 1.05 for z in [2.4, 5.2, 8.5, 11.6, 13.2, 14.6, 15.2, 13.8, 10.4, 6.2, 2.4]]
CT_ZB = [2.0, 4.0, 6.0, 7.2, 7.6, 7.4, 7.2, 6.6, 5.6, 4.0, 2.0]


def carapace_mesh():
    fw, ft, fb = pchip(CT_Y, CT_W), pchip(CT_Y, CT_ZT), pchip(CT_Y, CT_ZB)
    ys = np.linspace(CT_Y[0], CT_Y[-1], 46)
    secs = []
    for y in ys:
        w = max(float(fw(y)), 0.4)
        secs.append((float(y), w, max(float(ft(y)), 0.4), max(float(fb(y)), 0.4), 2.7, 0.0, 0.0))

    def displace(x, y, z):
        if z <= 0:
            return 0.0
        d = 0.0
        d -= 1.9 * math.exp(-((x / 1.7) ** 2 + ((y + 6.5) / 5.5) ** 2))                    # the thoracic fovea
        d -= 0.9 * math.exp(-((x / 9.0) ** 2) - ((y - 6.0) / 1.6) ** 2) * (1 - (abs(x) / 14.0) ** 2 if abs(x) < 14 else 0)  # the cervical groove
        d += 1.2 * float(U.smoothstep(2.0, 14.0, y))                                       # the head sits higher
        d -= 0.6 * math.exp(-(((abs(x) - 11.0) / 3.5) ** 2) - ((y + 6.0) / 5.0) ** 2)      # a pit where the legs' muscles lie
        return d
    return U.loft("carapace", secs, sides=36, displace=displace)


def build_carapace(sp, skin, hair_q):
    mat = MT.body("ct_" + skin, skin, "carapace")
    ct = add_obj("carapace", carapace_mesh(), mat, subsurf=(1, 2))
    sp.ct = ct
    sk = MT.SKINS[skin]
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(ct, dg)
    sp.eyes = []
    eye_big, eye_small = MT.eye("eye_big", skin, True), MT.eye("eye", skin, False)
    ring_m = MT.plain("eye_ring", sk["ring"], rough=0.35, coat=0.5)
    for kind, ex, ey, er in A.EYES:
        for side in (-1, 1):
            hit = bvh.ray_cast(Vector((side * ex, ey, 100.0)), Vector((0, 0, -1)))
            if hit[0] is None:
                continue
            loc, nrm = hit[0], hit[1]
            big = kind in ("AME", "ALE")
            me = U.sphere_mesh(f"eye_{kind}", er, 28, 18)
            eo = add_obj(f"eye_{kind}{side}", me, eye_big if big else eye_small, subsurf=None, parent=ct)
            eo.location = loc + nrm * (er * (0.12 if kind == "AME" else 0.2))
            eo.scale = (1.0, 1.0, 1.0)
            sp.eyes.append(eo)
            if kind in ("AME", "ALE") and skin == "spidey":
                tm = torus_mesh(er * 1.12, er * 0.34)
                ro = add_obj(f"ring_{kind}{side}", tm, ring_m, subsurf=(1, 2), parent=ct)
                ro.matrix_basis = Matrix.Translation(loc + nrm * (er * 0.05)) @ nrm.to_track_quat("Z", "Y").to_matrix().to_4x4()
    # the legs' sockets: a coxa at every hip, part of the body
    coxa_m = MT.plain("coxa", MT.rgb(14, 12, 16) if skin == "spidey" else MT.rgb(12, 8, 9), rough=0.3, coat=0.5)
    for side in (-1, 1):
        for i in (1, 2, 3, 4):
            hx, hy = A.HIPS[i]
            me = U.sphere_mesh("coxa", 1.0, 20, 12)
            co = add_obj(f"coxa{i}{side}", me, coxa_m, subsurf=(1, 1), parent=ct)
            co.location = (side * (hx - 2.0), hy, A.HIP_Z - A.CT_Z)
            co.scale = (7.0, 5.2, 4.6)
    # hair
    if hair_q > 0:
        area = surface_area(ct)
        hm = MT.hair_planar("hair_ct", skin, "carapace")
        pts = surface_points(ct, int(area * 0.85 * hair_q), seed=31, accept=lambda p, n: 1.0 if p.z > -2 else 0.1)
        make_hair("hair_ct", ct, pts, hm, length=(1.7, 3.3), radius=0.2, tilt=66, flow=(0, -1, 0), seed=31)
        beard_m = MT.hair_flat("beard", sk["beard"], rough=0.4)
        bp = surface_points(ct, int(area * 0.30 * hair_q), seed=42,
                            accept=lambda p, n: 1.0 if (p.y > 21.0 and n.z < 0.45) else 0.0)
        make_hair("beard", ct, bp, beard_m, length=(4.5, 8.0), radius=0.22, tilt=55, flow=(0, 0.6, -1), seed=42, points=4)
    return ct


def torus_mesh(R, r, seg=36, tub=10):
    bm = bmesh.new()
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ring = []
        for j in range(tub):
            b = 2 * math.pi * j / tub
            x = (R + r * math.cos(b)) * math.cos(a)
            y = (R + r * math.cos(b)) * math.sin(a)
            ring.append(bm.verts.new((x, y, r * math.sin(b) * 0.8)))
        rings.append(ring)
    for i in range(seg):
        for j in range(tub):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % tub], rings[(i + 1) % seg][(j + 1) % tub], rings[(i + 1) % seg][j]))
    me = bpy.data.meshes.new("torus")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


# ------------------------------------------------------------------------------------------------ face
def build_face(sp, skin, hair_q):
    sk = MT.SKINS[skin]
    chel_m = MT.plain("chelicera", sk["chel"], rough=0.26, coat=0.55)
    fang_m = MT.fang(skin)
    beard_m = MT.hair_flat("beard2", sk["beard"], rough=0.4)
    sp.chel = {}
    for side in (-1, 1):
        prof = pchip([0, 0.5, 1], [3.9, 3.6, 2.7])
        me = U.loft(f"chel", U.tube_secs(11.0, prof, rings=12), 14)
        ch = add_obj(f"chel{side}", me, chel_m, subsurf=(1, 2))
        fme = U.cone_mesh("fang", 7.0, 1.5, 0.12, bend=2.6)
        fg = add_obj(f"fang{side}", fme, fang_m, subsurf=(1, 1), parent=ch)
        fg.location = (0, 10.2, 0)
        sp.chel[side] = (ch, fg)
        if hair_q > 0:
            pts = surface_points(ch, int(70 * hair_q), seed=80 + side, accept=lambda p, n: 1.0 if n.y > -0.2 else 0.3)
            make_hair(f"chelhair{side}", ch, pts, beard_m, length=(3.5, 6.5), radius=0.2, tilt=60, flow=(0, 1, -0.4), seed=80 + side)
    # palps: three pieces, the last a club
    sp.palps = {}
    pal_m = MT.plain("palp", sk["chel"], rough=0.3, coat=0.4)
    profs = [pchip([0, 1], [2.4, 2.0]), pchip([0, 1], [2.0, 1.8]), pchip([0, 0.4, 0.8, 1.0], [1.6, 2.6, 2.3, 0.9])]
    for side in (-1, 1):
        parts = []
        for k in range(3):
            me = U.loft(f"palp{k}", U.tube_secs(A.PALP_LEN[k], profs[k], rings=10), 12)
            po = add_obj(f"palp{side}{k}", me, pal_m, subsurf=(1, 2))
            parts.append(po)
            if hair_q > 0:
                pts = surface_points(po, int((70 if k == 2 else 40) * hair_q), seed=700 + k + 3 * (side + 1))
                make_hair(f"palphair{side}{k}", po, pts, beard_m, length=(3.0, 6.0), radius=0.2, tilt=60, seed=710 + k + 3 * (side + 1))
        sp.palps[side] = parts


# ------------------------------------------------------------------------------------------------ the abdomen
AB_T = [0.0, 0.04, 0.10, 0.22, 0.38, 0.52, 0.66, 0.80, 0.91, 0.97, 1.0]
AB_W = [w * 1.10 for w in [3.6, 8.0, 15.0, 23.5, 27.5, 26.8, 23.0, 16.5, 9.5, 4.5, 2.2]]
AB_ZT = [z * 1.08 for z in [3.4, 8.0, 15.0, 27.0, 34.0, 34.5, 29.5, 21.0, 11.5, 5.5, 2.6]]
AB_ZB = [z * 1.08 for z in [3.2, 7.0, 11.0, 15.0, 17.5, 17.0, 14.0, 10.0, 6.0, 3.5, 2.2]]


def abdomen_mesh():
    fw, ft, fb = pchip(AB_T, AB_W), pchip(AB_T, AB_ZT), pchip(AB_T, AB_ZB)
    secs = []
    for t in np.linspace(0, 1, 44):
        y = 3.0 - A.AB_LEN * float(t)
        secs.append((y, max(float(fw(t)), 0.4), max(float(ft(t)), 0.4), max(float(fb(t)), 0.4), 2.35, 0.0, 0.0))
    return U.loft("abdomen", secs, sides=40)


def build_abdomen(sp, skin, hair_q):
    sk = MT.SKINS[skin]
    ab = add_obj("abdomen", abdomen_mesh(), MT.body("ab_" + skin, skin, "abdomen"), subsurf=(1, 2))
    sp.ab = ab
    # spinnerets
    sm = MT.plain("spinneret", MT.rgb(24, 16, 16), rough=0.4, coat=0.2)
    for side in (-1, 1):
        me = U.cone_mesh("spin", 5.5, 1.5, 0.7, bend=0.0)
        so = add_obj(f"spin{side}", me, sm, subsurf=(1, 1), parent=ab)
        so.location = (side * 1.7, 3.0 - A.AB_LEN + 1.0, 1.5)
        so.rotation_euler = (math.radians(100), 0, 0)
    if hair_q > 0:
        area = surface_area(ab)
        hm = MT.hair_planar("hair_ab", skin, "abdomen")
        pts = surface_points(ab, int(area * 0.70 * hair_q), seed=52)
        make_hair("hair_ab", ab, pts, hm, length=(1.9, 3.7), radius=0.22, tilt=70, flow=(0, -1, 0), curl=0.6, seed=52)
        gm = MT.hair_flat("guard", MT.rgb(10, 8, 12) if skin == "spidey" else MT.rgb(20, 10, 10), rough=0.3)
        gp = surface_points(ab, int(170 * hair_q), seed=55, accept=lambda p, n: 1.0 if n.z > -0.3 else 0.0)
        make_hair("guard_ab", ab, gp, gm, length=(6.5, 10.5), radius=0.30, tilt=62, flow=(0, -1, 0), curl=0.3, seed=55, tip=0.15, points=4)


# ------------------------------------------------------------------------------------------------ legs
RAD = {   # (t, radius) along the segment, before the per-leg scale
    "fem": [(0.0, 3.2), (0.05, 4.9), (0.18, 5.7), (0.45, 5.1), (0.75, 4.0), (0.93, 3.5), (1.0, 3.2)],
    "pat": [(0.0, 3.3), (0.5, 4.4), (1.0, 3.6)],
    "tib": [(0.0, 3.3), (0.12, 3.9), (0.32, 3.7), (0.70, 2.9), (1.0, 2.4)],
    "met": [(0.0, 2.5), (0.15, 2.7), (0.60, 2.0), (1.0, 1.55)],
    "tar": [(0.0, 1.65), (0.5, 1.25), (1.0, 0.7)],
}
# gentle curvature of each piece in its own frame: (+z = up/outward, x = sideways), so no limb is a ruler-straight pipe
BOW = {"fem": (2.6, 0.8), "pat": (0.0, 0.0), "tib": (2.2, 0.9), "met": (1.7, 0.7), "tar": (-1.3, 0.2)}
LEG_SCALE = {1: 1.0, 2: 0.97, 3: 0.92, 4: 1.0}
HAIR_D = {"fem": 0.20, "pat": 0.30, "tib": 0.22, "met": 0.20, "tar": 0.55}      # strands per BU^2
HAIR_LEN = {"fem": (2.0, 4.2), "pat": (1.8, 3.4), "tib": (2.0, 4.0), "met": (1.8, 3.6), "tar": (1.4, 2.8)}
SPINES = {"fem": 3, "pat": 0, "tib": 7, "met": 5, "tar": 0}


def leg_segment_mesh(seg, i, Lseg, side):
    k = LEG_SCALE[i] * 1.04
    ts = [p[0] for p in RAD[seg]]
    prof = pchip(ts, [p[1] * k for p in RAD[seg]])
    bz, bx = BOW[seg]
    sx = 1.0 if (i + side) % 2 else -1.0
    if seg == "tar":
        bend = lambda t: (sx * bx * math.sin(math.pi * t) * 0.3, bz * t * t)                  # the tarsus curls toward the ground
    else:
        bend = lambda t: (sx * bx * math.sin(math.pi * t), bz * math.sin(math.pi * t))
    return U.loft(f"leg_{seg}", U.tube_secs(Lseg, prof, rings=24, bend=bend, flat=0.93), 16)


def build_legs(sp, skin, hair_q):
    sk = MT.SKINS[skin]
    sp.legs, sp.leg_hair = {}, {}
    claw_m = MT.plain("claw", MT.rgb(14, 8, 8), rough=0.25, coat=0.3)
    spine_m = MT.hair_flat("spine", MT.rgb(12, 10, 14) if skin == "spidey" else MT.rgb(26, 12, 12), rough=0.25, coat=0.2)
    for side in (-1, 1):
        for i in (1, 2, 3, 4):
            segs = {}
            for seg in ("fem", "pat", "tib", "met", "tar"):
                Ls = A.LEG[i][seg]
                mat = MT.chitin(f"leg_{seg}_{i}{side}", skin, seg, Ls)
                ob = add_obj(f"{seg}{i}{side}", leg_segment_mesh(seg, i, Ls, side), mat, subsurf=(1, 2))
                segs[seg] = ob
                if hair_q > 0:
                    area = surface_area(ob)
                    hm = MT.hair_banded(f"hair_{seg}_{i}{side}", skin, seg, Ls)
                    n = int(area * HAIR_D[seg] * hair_q)
                    pts = surface_points(ob, n, seed=300 + i * 17 + (side + 1) * 5 + ord(seg[0]),
                                         accept=lambda p, nn, Ls=Ls: 1.0 if 0.07 * Ls < p.y < 0.95 * Ls else 0.06)
                    make_hair(f"h_{seg}{i}{side}", ob, pts, hm, length=HAIR_LEN[seg], radius=0.24, tilt=64, curl=0.45,
                              seed=310 + i * 7 + (side + 1) * 3 + ord(seg[0]))
                    ns = SPINES[seg]
                    if ns:
                        sp_pts = surface_points(ob, int(ns * (1.0 if hair_q >= 0.7 else 0.0)), seed=500 + i + ord(seg[0]),
                                                accept=lambda p, n: 1.0 if n.z > -0.2 else 0.0)
                        make_hair(f"s_{seg}{i}{side}", ob, sp_pts, spine_m, length=(6.5, 9.5), radius=0.38, tilt=58, straight=True,
                                  seed=520 + i, tip=0.12, points=3)
            # the claws: two small hooks at the foot
            for c, ang in enumerate((-18, 18)):
                cm = U.cone_mesh("claw", 3.6, 0.75, 0.08, bend=1.6)
                co = add_obj(f"claw{i}{side}{c}", cm, claw_m, subsurf=(1, 1), parent=segs["tar"])
                co.location = (0, A.LEG[i]["tar"] - 0.6, 0)
                co.rotation_euler = (0, math.radians(ang), 0)
            sp.legs[(side, i)] = segs


def build(skin="spidey", hair=1.0):
    sp = Spider()
    sp.skin = skin
    build_carapace(sp, skin, hair)
    build_face(sp, skin, hair)
    build_abdomen(sp, skin, hair)
    build_legs(sp, skin, hair)
    return sp
