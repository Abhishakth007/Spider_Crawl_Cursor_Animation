"""The spider, modelled in Blender from code.

A jumping-spider build (eight eyes, big forward pair, iridescent chelicerae, banded hairy legs) in the gold-and-indigo
of the portfolio. Everything is lofted from cross-sections, so the proportions are numbers, not sculpting:

  carapace    superellipse sections, blunt face, domed thorax
  abdomen     egg with a tapering rear, spinnerets, a pedicel into the carapace
  legs        3 rigid parts per leg, each a swollen tube with a ball at its joint (the balls overlap, so a bend never gaps)
              B1 trochanter + femur, B2 patella + tibia, B3 metatarsus + tarsus + claws
  palps       3 short parts per side, clubbed at the tip
  chelicerae  one chunky part and a curved fang per side
  fur         thousands of hair curves (Cycles hair) scattered on the evaluated surface, plus stiff spines on the legs

Nothing is parented through an armature: each rigid part is placed by spider_motion.py, and the fur is a child of its part.
Units are Blender units; the spider faces +Y, stands on z = 0, and is about 136 long and 240 across the feet.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix

GOLD = (0.88, 0.45, 0.02, 1.0)          # the abdomen's amber
LEG_GOLD = (0.74, 0.31, 0.012, 1.0)
GOLD_HI = (1.0, 0.60, 0.11, 1.0)        # fur
CREAM = (0.95, 0.78, 0.46, 1.0)
NAVY = (0.011, 0.011, 0.065, 1.0)
INDIGO = (0.03, 0.025, 0.20, 1.0)

# ------------------------------------------------------------------------------------------ the numbers
CT_LEN, CT_W, CT_HT, CT_HB, CT_Z = 56.0, 22.0, 17.0, 7.5, 21.0     # carapace: length, half width, top, bottom, centre height
AB_LEN, AB_W, AB_HT, AB_HB = 78.0, 26.0, 24.0, 21.0
AB_ATTACH = Vector((0.0, -27.0, 2.0))                               # abdomen's front point, relative to the carapace centre
AB_TILT = math.radians(9)                                            # nose-up, in the rest pose
HIP_Z = 17.5
HIPS = {1: (16.0, 14.5), 2: (18.0, 5.0), 3: (18.0, -5.0), 4: (16.5, -14.5)}   # (x, y) of each coxa on the carapace's side
LEG_SCALE = {1: 1.03, 2: 0.94, 3: 0.91, 4: 1.10}
B1, B2, B3 = 54.0, 56.0, 66.0                                        # rigid part lengths at scale 1

rng = random.Random(11)


# ------------------------------------------------------------------------------------------ meshes
def _se(th, n):
    c, s = math.cos(th), math.sin(th)
    e = 2.0 / n
    return math.copysign(abs(c) ** e, c), math.copysign(abs(s) ** e, s)


def loft(name, secs, sides=16):
    """secs: (y, half width, top, bottom, superellipse n, cx, cz) rings along +Y, closed with a fan at each end."""
    bm = bmesh.new()
    rings = []
    for (y, wx, zt, zb, n, cx, cz) in secs:
        ring = []
        for k in range(sides):
            ux, uz = _se(2 * math.pi * k / sides, n)
            ring.append(bm.verts.new((cx + wx * ux, y, cz + (zt * uz if uz >= 0 else zb * uz))))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
    for ring, first in ((rings[0], True), (rings[-1], False)):
        c = Vector((sum(v.co.x for v in ring), sum(v.co.y for v in ring), sum(v.co.z for v in ring))) / sides
        cv = bm.verts.new(c)
        for k in range(sides):
            a, b = ring[k], ring[(k + 1) % sides]
            bm.faces.new((cv, b, a) if first else (cv, a, b))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def _prof(kn, t):
    if t <= kn[0][0]:
        return kn[0][1]
    for (t0, v0), (t1, v1) in zip(kn, kn[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            u = u * u * (3 - 2 * u)
            return v0 + (v1 - v0) * u
    return kn[-1][1]


def tube_secs(L, kn, rings=22, flat=0.94, ball0=True, ball1=True, bend=None):
    """Sections for a tube from y=0 to y=L whose radius follows the knots kn = [(t, r)], with a sphere at either end
    centred on the joint (so neighbouring parts overlap in a ball joint). bend(t) -> (cx, cz) curves the axis."""
    bend = bend or (lambda t: (0.0, 0.0))
    secs = []
    r0, r1 = _prof(kn, 0.0), _prof(kn, 1.0)
    if ball0:
        for a in (0.32, 0.72, 1.08, 1.38):
            cx, cz = bend(0.0)
            secs.append((-r0 * math.cos(a), r0 * math.sin(a), r0 * math.sin(a) * flat, r0 * math.sin(a) * flat, 2.0, cx, cz))
    for i in range(rings + 1):
        t = i / rings
        r = _prof(kn, t)
        cx, cz = bend(t)
        secs.append((L * t, r, r * flat, r * flat, 2.0, cx, cz))
    if ball1:
        for a in (1.38, 1.08, 0.72, 0.32):
            cx, cz = bend(1.0)
            secs.append((L + r1 * math.cos(a), r1 * math.sin(a), r1 * math.sin(a) * flat, r1 * math.sin(a) * flat, 2.0, cx, cz))
    return secs


def carapace_secs(count=34):
    secs = []
    t0 = 0.36
    for i in range(count + 1):
        t = i / count
        y = -CT_LEN / 2 + CT_LEN * t
        if t < t0:
            s, p = (t0 - t) / t0, 2.3
        else:
            s, p = (t - t0) / (1 - t0), 3.3
        w = CT_W * max(1e-3, (1 - min(1, s) ** p)) ** (1 / p)
        k = w / CT_W
        hs = 1.0 - 0.18 * max(0.0, (t - 0.5) / 0.5) ** 1.4
        zt = CT_HT * k ** 0.55 * hs
        zb = CT_HB * k ** 0.5
        secs.append((y, max(w, 0.35), max(zt, 0.3), max(zb, 0.3), 2.6, 0.0, 0.0))
    return secs


def abdomen_secs(count=36):
    secs = [(8.0, 3.6, 3.4, 3.2, 2.0, 0.0, 0.0), (3.0, 4.4, 4.2, 4.0, 2.0, 0.0, 0.0)]       # the pedicel, tucked into the carapace
    for i in range(1, count + 1):
        t = i / count
        s = math.sin(math.pi * t ** 0.72)
        s = max(s, 0.04)
        secs.append((-AB_LEN * t, AB_W * s, AB_HT * s ** 0.85, AB_HB * s ** 0.85, 2.1, 0.0, 0.0))
    return secs


def make_obj(name, me, mat, subsurf=2, view=1):
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat:
        me.materials.append(mat)
    if subsurf:
        m = ob.modifiers.new("sub", "SUBSURF")
        m.levels, m.render_levels = view, subsurf
    return ob


# ------------------------------------------------------------------------------------------ materials
def _mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, m.node_tree


def _n(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def _coord(nt, axis, scale):
    """Object-space coordinate along an axis, divided by `scale`."""
    tc = _n(nt, "ShaderNodeTexCoord")
    sp = _n(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sp.inputs[0])
    mul = _n(nt, "ShaderNodeMath", operation="MULTIPLY")
    mul.inputs[1].default_value = 1.0 / scale
    nt.links.new(sp.outputs[axis], mul.inputs[0])
    return tc, sp, mul.outputs[0]


def chitin(name, base=NAVY, rough=0.34, coat=0.35, bump=0.12, bands=None, axis=1, scale=1.0, noise_warp=0.02, tint=None):
    """A glossy cuticle. `bands` = [(t_end, colour)] along an object axis (t = coordinate / scale), constant steps with a
    little noise in the edges so the rings are not ruler-straight."""
    m, nt = _mat(name)
    out, bs = _n(nt, "ShaderNodeOutputMaterial"), _n(nt, "ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs[0], out.inputs[0])
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Coat Weight"].default_value = coat
    bs.inputs["Coat Roughness"].default_value = 0.12
    bs.inputs["Specular IOR Level"].default_value = 0.6
    if bands:
        tc, sp, t = _coord(nt, 1 if axis == 1 else axis, scale)
        nz = _n(nt, "ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 3.0, 3.0
        nt.links.new(tc.outputs["Object"], nz.inputs[0])
        add = _n(nt, "ShaderNodeMath", operation="MULTIPLY_ADD")
        nt.links.new(nz.outputs["Fac"], add.inputs[0]); add.inputs[1].default_value = noise_warp * 2
        add.inputs[2].default_value = -noise_warp
        s2 = _n(nt, "ShaderNodeMath", operation="ADD")
        nt.links.new(t, s2.inputs[0]); nt.links.new(add.outputs[0], s2.inputs[1])
        ramp = _n(nt, "ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "CONSTANT"
        els = ramp.color_ramp.elements
        prev = 0.0
        for k, (te, col) in enumerate(bands):
            if k >= len(els):
                els.new(prev)
            els[k].position = prev
            els[k].color = col
            prev = te
        nt.links.new(s2.outputs[0], ramp.inputs[0])
        col_out = ramp.outputs[0]
    else:
        rgb = _n(nt, "ShaderNodeRGB")
        rgb.outputs[0].default_value = base
        col_out = rgb.outputs[0]
    nt.links.new(col_out, bs.inputs["Base Color"])
    if bump:
        tc2 = _n(nt, "ShaderNodeTexCoord")
        nz = _n(nt, "ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 18.0, 8.0
        nt.links.new(tc2.outputs["Object"], nz.inputs[0])
        bp = _n(nt, "ShaderNodeBump")
        bp.inputs["Strength"].default_value, bp.inputs["Distance"].default_value = bump, 0.4
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs[0], bs.inputs["Normal"])
    return m


def abdomen_mat():
    """Gold with indigo chevrons (V's pointing at the head), a darker belly, and a few spots on the flanks."""
    m, nt = _mat("abdomen")
    out, bs = _n(nt, "ShaderNodeOutputMaterial"), _n(nt, "ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs[0], out.inputs[0])
    bs.inputs["Roughness"].default_value = 0.42
    bs.inputs["Coat Weight"].default_value = 0.25
    bs.inputs["Coat Roughness"].default_value = 0.2
    tc = _n(nt, "ShaderNodeTexCoord")
    sp = _n(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sp.inputs[0])
    ax = _n(nt, "ShaderNodeMath", operation="ABSOLUTE"); nt.links.new(sp.outputs[0], ax.inputs[0])
    # u = -y * k1 + |x| * k2  (V-shaped lines), with noise in it
    ay = _n(nt, "ShaderNodeMath", operation="MULTIPLY"); ay.inputs[1].default_value = -0.105
    nt.links.new(sp.outputs[1], ay.inputs[0])
    axk = _n(nt, "ShaderNodeMath", operation="MULTIPLY"); axk.inputs[1].default_value = 0.085
    nt.links.new(ax.outputs[0], axk.inputs[0])
    u = _n(nt, "ShaderNodeMath", operation="ADD")
    nt.links.new(ay.outputs[0], u.inputs[0]); nt.links.new(axk.outputs[0], u.inputs[1])
    nz = _n(nt, "ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.09; nz.inputs["Detail"].default_value = 4
    nt.links.new(tc.outputs["Object"], nz.inputs[0])
    nzs = _n(nt, "ShaderNodeMath", operation="MULTIPLY_ADD"); nzs.inputs[1].default_value = 0.9; nzs.inputs[2].default_value = -0.45
    nt.links.new(nz.outputs["Fac"], nzs.inputs[0])
    u2 = _n(nt, "ShaderNodeMath", operation="ADD"); nt.links.new(u.outputs[0], u2.inputs[0]); nt.links.new(nzs.outputs[0], u2.inputs[1])
    wv = _n(nt, "ShaderNodeMath", operation="SINE")
    uk = _n(nt, "ShaderNodeMath", operation="MULTIPLY"); uk.inputs[1].default_value = 2 * math.pi
    nt.links.new(u2.outputs[0], uk.inputs[0]); nt.links.new(uk.outputs[0], wv.inputs[0])
    # fade the chevrons out toward the belly and the flanks
    az = _n(nt, "ShaderNodeMapRange"); az.inputs[1].default_value, az.inputs[2].default_value = -3.0, 7.0
    az.inputs[3].default_value, az.inputs[4].default_value = 0.0, 1.0
    nt.links.new(sp.outputs[2], az.inputs[0])
    thr = _n(nt, "ShaderNodeMapRange"); thr.inputs[1].default_value, thr.inputs[2].default_value = 0.30, 0.50
    thr.inputs[3].default_value, thr.inputs[4].default_value = 0.0, 1.0
    nt.links.new(wv.outputs[0], thr.inputs[0])
    stripe = _n(nt, "ShaderNodeMath", operation="MULTIPLY")
    nt.links.new(thr.outputs[0], stripe.inputs[0]); nt.links.new(az.outputs[0], stripe.inputs[1])
    # a lighter front cap
    fy = _n(nt, "ShaderNodeMapRange"); fy.inputs[1].default_value, fy.inputs[2].default_value = -6.0, -16.0
    fy.inputs[3].default_value, fy.inputs[4].default_value = 0.0, 1.0
    nt.links.new(sp.outputs[1], fy.inputs[0])
    st2 = _n(nt, "ShaderNodeMath", operation="MULTIPLY"); nt.links.new(stripe.outputs[0], st2.inputs[0]); nt.links.new(fy.outputs[0], st2.inputs[1])
    mix = _n(nt, "ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs[6].default_value = GOLD; mix.inputs[7].default_value = INDIGO
    nt.links.new(st2.outputs[0], mix.inputs[0])
    # spots
    vor = _n(nt, "ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 0.16
    nt.links.new(tc.outputs["Object"], vor.inputs[0])
    sm = _n(nt, "ShaderNodeMapRange"); sm.inputs[1].default_value, sm.inputs[2].default_value = 0.30, 0.22
    nt.links.new(vor.outputs["Distance"], sm.inputs[0])
    mix2 = _n(nt, "ShaderNodeMix"); mix2.data_type = "RGBA"; mix2.inputs[7].default_value = NAVY
    nt.links.new(sm.outputs[0], mix2.inputs[0]); nt.links.new(mix.outputs[2], mix2.inputs[6])
    # belly
    bz = _n(nt, "ShaderNodeMapRange"); bz.inputs[1].default_value, bz.inputs[2].default_value = -2.0, -10.0
    nt.links.new(sp.outputs[2], bz.inputs[0])
    mix3 = _n(nt, "ShaderNodeMix"); mix3.data_type = "RGBA"; mix3.inputs[7].default_value = NAVY
    nt.links.new(bz.outputs[0], mix3.inputs[0]); nt.links.new(mix2.outputs[2], mix3.inputs[6])
    nt.links.new(mix3.outputs[2], bs.inputs["Base Color"])
    tc2 = _n(nt, "ShaderNodeTexCoord"); nz2 = _n(nt, "ShaderNodeTexNoise")
    nz2.inputs["Scale"].default_value, nz2.inputs["Detail"].default_value = 22.0, 6.0
    nt.links.new(tc2.outputs["Object"], nz2.inputs[0])
    bp = _n(nt, "ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.1
    nt.links.new(nz2.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], bs.inputs["Normal"])
    return m


def iridescent(name):
    """Chelicerae: a metallic teal-to-violet that turns with the angle, the way a jumping spider's do."""
    m, nt = _mat(name)
    out, bs = _n(nt, "ShaderNodeOutputMaterial"), _n(nt, "ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs[0], out.inputs[0])
    bs.inputs["Metallic"].default_value = 0.85
    bs.inputs["Roughness"].default_value = 0.22
    bs.inputs["Coat Weight"].default_value = 0.5
    lw = _n(nt, "ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.4
    ramp = _n(nt, "ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.0, 0.32, 0.30, 1)
    ramp.color_ramp.elements[1].color = (0.30, 0.04, 0.55, 1)
    nt.links.new(lw.outputs["Facing"], ramp.inputs[0]); nt.links.new(ramp.outputs[0], bs.inputs["Base Color"])
    return m


def fang_mat():
    m, nt = _mat("fang")
    out, bs = _n(nt, "ShaderNodeOutputMaterial"), _n(nt, "ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs[0], out.inputs[0])
    bs.inputs["Base Color"].default_value = (0.22, 0.06, 0.012, 1)
    bs.inputs["Roughness"].default_value = 0.18
    bs.inputs["Coat Weight"].default_value = 0.6
    bs.inputs["Subsurface Weight"].default_value = 0.3
    bs.inputs["Subsurface Radius"].default_value = (1.0, 0.4, 0.2)
    bs.inputs["Subsurface Scale"].default_value = 0.8
    return m


def eye_mat(big):
    """A black lens with a hard highlight; the big forward eyes get a faint amber retina behind it."""
    m, nt = _mat("eye_big" if big else "eye")
    out, bs = _n(nt, "ShaderNodeOutputMaterial"), _n(nt, "ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs[0], out.inputs[0])
    bs.inputs["Base Color"].default_value = (0.004, 0.004, 0.006, 1)
    bs.inputs["Roughness"].default_value = 0.04
    bs.inputs["Coat Weight"].default_value = 1.0
    bs.inputs["Coat Roughness"].default_value = 0.02
    bs.inputs["Specular IOR Level"].default_value = 1.0
    if big:
        lw = _n(nt, "ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
        mr = _n(nt, "ShaderNodeMapRange"); mr.inputs[1].default_value, mr.inputs[2].default_value = 0.35, 0.0
        mr.inputs[3].default_value, mr.inputs[4].default_value = 0.0, 1.0
        nt.links.new(lw.outputs["Facing"], mr.inputs[0])
        em = _n(nt, "ShaderNodeMath", operation="MULTIPLY"); em.inputs[1].default_value = 0.07
        nt.links.new(mr.outputs[0], em.inputs[0])
        bs.inputs["Emission Color"].default_value = (0.9, 0.38, 0.04, 1)
        nt.links.new(em.outputs[0], bs.inputs["Emission Strength"])
    return m


def hair_mat(name, bands=None, color=CREAM, rough=0.32, axis=1, scale=1.0, dark=None):
    """Principled Hair (Direct colouring). With `bands` the colour steps along an object axis like the skin it grows from."""
    m, nt = _mat(name)
    out, hb = _n(nt, "ShaderNodeOutputMaterial"), _n(nt, "ShaderNodeBsdfHairPrincipled")
    hb.parametrization = "COLOR"
    nt.links.new(hb.outputs[0], out.inputs[0])
    hb.inputs["Roughness"].default_value = rough
    hb.inputs["Radial Roughness"].default_value = 0.45
    hb.inputs["Coat"].default_value = 0.1
    hb.inputs["IOR"].default_value = 1.55
    for k, v in (("Random Color", 0.12), ("Random Roughness", 0.2)):
        if k in hb.inputs:
            hb.inputs[k].default_value = v
    if bands:
        tc, sp, t = _coord(nt, axis, scale)
        ramp = _n(nt, "ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "CONSTANT"
        els = ramp.color_ramp.elements
        prev = 0.0
        for k, (te, col) in enumerate(bands):
            if k >= len(els):
                els.new(prev)
            els[k].position = prev
            els[k].color = col
            prev = te
        nt.links.new(t, ramp.inputs[0])
        nt.links.new(ramp.outputs[0], hb.inputs["Color"])
    else:
        hb.inputs["Color"].default_value = color
    return m


# ------------------------------------------------------------------------------------------ fur
def surface_points(ob, n, accept=None, seed=1):
    """n (position, normal) samples on the evaluated surface of ob, in its local space, area-weighted;
    accept(p, nrm) -> probability keeps a pattern in the density."""
    r = random.Random(seed)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    vn = [v.normal.copy() for v in me.vertices]
    co = [v.co.copy() for v in me.vertices]
    tris = [t.vertices[:] for t in me.loop_triangles]
    acc, tot = [], 0.0
    for a, b, c in tris:
        tot += ((co[b] - co[a]).cross(co[c] - co[a])).length * 0.5
        acc.append(tot)
    import bisect
    pts = []
    guard = 0
    while len(pts) < n and guard < n * 40:
        guard += 1
        k = bisect.bisect_left(acc, r.random() * tot)
        a, b, c = tris[min(k, len(tris) - 1)]
        u, v = r.random(), r.random()
        if u + v > 1:
            u, v = 1 - u, 1 - v
        w = 1 - u - v
        p = co[a] * w + co[b] * u + co[c] * v
        nrm = (vn[a] * w + vn[b] * u + vn[c] * v).normalized()
        if accept is not None and r.random() > accept(p, nrm):
            continue
        pts.append((p, nrm))
    ev.to_mesh_clear()
    return pts


def mirror_x(pts):
    return [(Vector((-p.x, p.y, p.z)), Vector((-n.x, n.y, n.z))) for p, n in pts]


def make_hair(name, parent, pts, mat, length=(4.0, 7.0), radius=0.22, tilt=62.0, flow=(0.0, 1.0, 0.0), curl=0.55, jitter=14.0,
              straight=False, seed=3, tip=0.25):
    """One Curves object of 3-point strands rooted at pts, growing along the surface normal and bending toward `flow`."""
    r = random.Random(seed)
    cu = bpy.data.hair_curves.new(name)
    n = len(pts)
    cu.add_curves([3] * n)
    pos, rad = [], []
    fl = Vector(flow).normalized()
    for p, nrm in pts:
        t = fl - nrm * fl.dot(nrm)
        t = t.normalized() if t.length > 1e-4 else Vector((0, 0, 1))
        side = nrm.cross(t)
        ang = math.radians(tilt + r.gauss(0, jitter))
        sj = math.radians(r.gauss(0, jitter))
        d = (nrm * math.cos(ang) + t * math.sin(ang)) * math.cos(sj) + side * math.sin(sj)
        d = d.normalized()
        ln = r.uniform(*length)
        if straight:
            q1, q2 = p + d * ln * 0.5, p + d * ln
        else:
            q1 = p + (nrm * 0.75 + d * 0.25).normalized() * ln * 0.5
            q2 = q1 + (d * (1 - curl) + t * curl * 0.9 + nrm * 0.1).normalized() * ln * 0.5
        base = p - nrm * 0.5
        pos += [*base, *q1, *q2]
        rad += [radius, radius * 0.85, radius * tip]
    cu.points.foreach_set("position", pos)
    cu.points.foreach_set("radius", rad)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.matrix_parent_inverse = Matrix.Identity(4)
    cu.materials.append(mat)
    return ob


# ------------------------------------------------------------------------------------------ the spider
class Spider:
    pass


def hair_set(seg_name, ob, mats, count, side_mirror, seed, **kw):
    pts = surface_points(ob, count, seed=seed, accept=kw.pop("accept", None))
    return pts


def build():
    sp = Spider()
    sp.parts = []
    # ---- materials
    leg_b1 = [(0.10, NAVY), (0.80, LEG_GOLD), (1.0, NAVY)]
    leg_b2 = [(0.17, NAVY), (0.30, LEG_GOLD), (0.80, LEG_GOLD), (1.0, NAVY)]
    leg_b3 = [(0.20, LEG_GOLD), (0.58, LEG_GOLD), (0.70, NAVY), (0.78, LEG_GOLD), (1.0, NAVY)]
    m_ct = chitin("carapace", base=NAVY, rough=0.34, coat=0.3, bump=0.1)
    m_leg = [chitin(f"leg_b{k}", bands=b, scale=L, rough=0.36, coat=0.3, bump=0.14)
             for k, (b, L) in enumerate(((leg_b1, B1), (leg_b2, B2), (leg_b3, B3)), 1)]
    m_ab = abdomen_mat()
    m_palp = chitin("palp", bands=[(0.55, LEG_GOLD), (1.0, NAVY)], scale=22.0, rough=0.4, coat=0.2, bump=0.1)
    m_chel, m_fang = iridescent("chelicera"), fang_mat()
    m_eye, m_eyeb = eye_mat(False), eye_mat(True)
    h_cream = hair_mat("hair_cream", color=CREAM)
    h_gold = hair_mat("hair_gold", color=GOLD_HI, rough=0.3)
    h_navy = hair_mat("hair_navy", color=(0.03, 0.028, 0.16, 1), rough=0.35)
    h_legs = [hair_mat(f"hair_leg_b{k}", bands=[(a, GOLD_HI if c is LEG_GOLD else (0.06, 0.05, 0.26, 1)) for a, c in b], scale=L, rough=0.3)
              for k, (b, L) in enumerate(((leg_b1, B1), (leg_b2, B2), (leg_b3, B3)), 1)]
    spine_m = hair_mat("spine", color=(0.04, 0.035, 0.16, 1), rough=0.25)

    # ---- carapace
    ct = make_obj("CT", loft("CT", carapace_secs(), sides=32), m_ct, subsurf=2)
    sp.ct = ct
    # ---- abdomen
    ab = make_obj("AB", loft("AB", abdomen_secs(), sides=36), m_ab, subsurf=2)
    sp.ab = ab
    # spinnerets
    sp.spin = []
    for sx in (-1, 1):
        for lvl, (yy, zz, xx) in enumerate(((-AB_LEN - 0.5, -4.0, 2.6), (-AB_LEN + 2.0, -1.0, 2.0))):
            me = loft("sp", tube_secs(6.5, [(0, 2.2), (1, 1.5)], rings=5, ball0=False, ball1=True), sides=10)
            o = make_obj("spinneret", me, m_palp, subsurf=1)
            o.parent = ab
            o.location = (sx * xx, yy, zz)
            o.rotation_euler = (math.radians(100 + 8 * lvl), 0, math.radians(-sx * 10))
            sp.spin.append(o)

    # ---- legs
    sp.legs = {}
    sp.leg_len = {}
    for i in (1, 2, 3, 4):
        sc = LEG_SCALE[i]
        lens = (B1 * sc, B2 * sc, B3 * sc)
        sp.leg_len[i] = lens
        for side in (-1, 1):
            segs = []
            profs = (
                [(0, 5.2), (0.09, 3.9), (0.20, 4.3), (0.55, 4.45), (1.0, 3.5)],
                [(0, 3.8), (0.13, 3.4), (0.22, 3.15), (0.60, 3.15), (1.0, 2.6)],
                [(0, 2.7), (0.45, 2.35), (0.66, 2.05), (0.69, 2.15), (1.0, 1.2)],
            )
            for k in range(3):
                kn = [(t, r * (0.5 + 0.5 * sc)) for t, r in profs[k]]
                me = loft(f"leg{i}{side}b{k+1}", tube_secs(lens[k], kn, rings=22 if k < 2 else 26, flat=0.93), sides=12)
                segs.append(make_obj(f"Leg{i}{'L' if side < 0 else 'R'}_B{k+1}", me, m_leg[k], subsurf=2))
            # claws at the tip of B3
            for cs in (-1, 1):
                me = loft("claw", tube_secs(4.6, [(0, 0.55), (1, 0.12)], rings=4, ball0=False, ball1=False,
                                            bend=lambda t: (0.0, -1.3 * t * t)), sides=6)
                c = make_obj("claw", me, m_fang, subsurf=0)
                c.parent = segs[2]
                c.location = (cs * 0.9, lens[2] + 0.6, 0)
                c.rotation_euler = (math.radians(70), 0, math.radians(cs * 22))
            sp.legs[(side, i)] = segs

    # ---- palps (3 parts per side) and chelicerae
    sp.palps, sp.chel = {}, {}
    for side in (-1, 1):
        parts = []
        for k, (L, r0, r1) in enumerate(((11.0, 2.7, 2.4), (9.0, 2.3, 2.1), (8.0, 2.2, 1.7))):
            kn = [(0, r0), (1, r1)]
            if k == 2:
                kn = [(0, r0), (0.4, 1.9), (0.75, 2.6), (1.0, 1.7)]
            parts.append(make_obj(f"Palp{'L' if side < 0 else 'R'}{k+1}", loft("palp", tube_secs(L, kn, rings=8), sides=12), m_palp, subsurf=1))
        sp.palps[side] = parts
        ch = make_obj(f"Chel{'L' if side < 0 else 'R'}", loft("chel", tube_secs(13.0, [(0, 4.6), (0.5, 5.0), (1, 3.8)], rings=8, flat=1.0), sides=14), m_chel, subsurf=2)
        fg = make_obj("fang", loft("fang", tube_secs(13.0, [(0, 2.1), (0.5, 1.4), (1, 0.18)], rings=10, ball0=False, ball1=False,
                                                       bend=lambda t, s=side: (-s * 3.0 * t * t, 0.0)), sides=10), m_fang, subsurf=1)
        fg.parent = ch
        fg.location = (-side * 0.2, 11.5, 0.5)
        fg.rotation_euler = (math.radians(-10), 0, 0)
        sp.chel[side] = (ch, fg)

    # ---- eyes: the jumping-spider eight. Find where each sits on the evaluated carapace, so it is embedded on the surface
    dg = bpy.context.evaluated_depsgraph_get()
    eyes = []
    layout = (  # name, (x, y) on the top / front, radius, big, aim: 'front' casts along -y from the front, 'down' casts along -z
        ("AME", (5.4, 40.0, 4.3), 5.3, True, "front"),
        ("ALE", (12.2, 31.0, 7.6), 3.3, False, "front"),
        ("PME", (11.6, 15.5, 30.0), 1.15, False, "down"),
        ("PLE", (15.2, 9.5, 30.0), 3.5, False, "down"),
    )
    for nm, (x, y, z), r, big, aim in layout:
        for side in (-1, 1):
            origin = Vector((side * x, y, z))
            dirv = Vector((0, -1, 0)) if aim == "front" else Vector((0, 0, -1))
            hit, loc, nrm, idx = ct.ray_cast(origin, dirv, depsgraph=dg)
            if not hit:
                print("EYE MISS", nm, side)
                continue
            center = loc + nrm.normalized() * (r * 0.42)
            me = bpy.data.meshes.new("eye")
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=r)
            bm.to_mesh(me); bm.free()
            for p in me.polygons:
                p.use_smooth = True
            e = make_obj(f"Eye{nm}{'L' if side < 0 else 'R'}", me, m_eyeb if big else m_eye, subsurf=0)
            e.parent = ct
            e.location = center
            eyes.append(e)
            # a dark socket ring around each eye
            me2 = bpy.data.meshes.new("socket")
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=r * 1.2)
            bm.to_mesh(me2); bm.free()
            for p in me2.polygons:
                p.use_smooth = True
            s = make_obj("socket", me2, m_ct, subsurf=0)
            s.parent = ct
            s.location = center - nrm.normalized() * (r * 0.66)
    sp.eyes = eyes

    # ---- fur
    S = 5
    def body_accept(p, nrm):
        return 1.0
    # carapace: a gold stripe down the middle, cream fringe round the margin and a cream "beard" under the big eyes
    def ct_accept(p, nrm):
        edge = 1.0 - abs(nrm.z)
        mid = max(0.0, 1.0 - abs(p.x) / 4.5)
        face = 1.0 if (p.y > 22 and p.z < 4) else 0.0
        return min(1.0, 0.10 + 0.9 * edge ** 1.5 + 0.8 * mid * (p.z > 5) + 0.9 * face)
    pts = surface_points(ct, 9000, accept=ct_accept, seed=21)
    pts = [(p, n) for p, n in pts if p.x >= -0.2]
    pts = pts + mirror_x(pts)
    make_hair("hair_ct_a", ct, pts[: len(pts) // 2], h_cream, length=(2.6, 5.4), radius=0.22, tilt=68, flow=(0, -1, 0), seed=31)
    make_hair("hair_ct_b", ct, pts[len(pts) // 2:], h_gold, length=(2.6, 5.4), radius=0.22, tilt=68, flow=(0, -1, 0), seed=32)
    # the beard: longer, straight down and forward
    beard = surface_points(ct, 420, accept=lambda p, n: 1.0 if (p.y > 22 and p.z < 3 and p.x > 0) else 0.0, seed=41)
    beard = beard + mirror_x(beard)
    make_hair("hair_beard", ct, beard, h_cream, length=(4.0, 7.5), radius=0.22, tilt=58, flow=(0, 0.7, -1), seed=42)

    def ab_accept(p, nrm):
        return 1.0
    pts = surface_points(ab, 5600, accept=ab_accept, seed=51)
    pts = [(p, n) for p, n in pts if p.x >= -0.2 and p.y < 1.0]
    pts = pts + mirror_x(pts)
    half = len(pts) // 2
    make_hair("hair_ab_a", ab, pts[:half], h_gold, length=(2.6, 4.8), radius=0.24, tilt=70, flow=(0, -1, 0), curl=0.6, seed=52)
    make_hair("hair_ab_b", ab, pts[half:], h_cream, length=(2.4, 4.4), radius=0.22, tilt=72, flow=(0, -1, 0), curl=0.6, seed=53)
    # a few long dark guard hairs
    gh = surface_points(ab, 150, seed=54, accept=lambda p, n: 1.0 if p.y < -6 else 0.0)
    gh = gh + mirror_x(gh)
    make_hair("hair_ab_guard", ab, gh, h_navy, length=(8, 13), radius=0.3, tilt=62, flow=(0, -1, 0), curl=0.3, seed=55, tip=0.15)

    # legs: fur on each part (mirrored for the right side), plus spines
    for i in (1, 2, 3, 4):
        for k in range(3):
            base = surface_points(sp.legs[(-1, i)][k], (380, 340, 420)[k], seed=100 + 10 * i + k,
                                  accept=lambda p, n, L=sp.leg_len[i][k]: 1.0 if 0.06 * L < p.y < 0.98 * L else 0.0)
            spn = surface_points(sp.legs[(-1, i)][k], (0, 7, 7)[k], seed=200 + 10 * i + k,
                                 accept=lambda p, n, L=sp.leg_len[i][k]: 1.0 if (0.1 * L < p.y < 0.9 * L and abs(n.z) < 0.7) else 0.0)
            for side in (-1, 1):
                seg = sp.legs[(side, i)][k]
                pts = base if side < 0 else mirror_x(base)
                make_hair(f"hair_l{i}{side}{k}", seg, pts, h_legs[k], length=(2.8, 5.2), radius=0.2, tilt=60, curl=0.5, seed=300 + i * 10 + k)
                if spn:
                    pts = spn if side < 0 else mirror_x(spn)
                    make_hair(f"spine_l{i}{side}{k}", seg, pts, spine_m, length=(8.5, 12.5), radius=0.42, tilt=52, straight=True,
                              seed=400 + i * 10 + k, tip=0.18)
        # a tuft round each foot
        for side in (-1, 1):
            seg = sp.legs[(side, i)][2]
            L = sp.leg_len[i][2]
            tuft = surface_points(sp.legs[(-1, i)][2], 90, seed=500 + i, accept=lambda p, n, L=L: 1.0 if p.y > 0.8 * L else 0.0)
            make_hair(f"tuft_{i}{side}", seg, tuft if side < 0 else mirror_x(tuft), h_cream, length=(3.0, 5.0), radius=0.2, tilt=75, seed=600 + i)
    # palps are furry
    for side in (-1, 1):
        for k, o in enumerate(sp.palps[side]):
            pts = surface_points(o, 120, seed=700 + k)
            make_hair(f"hair_palp{side}{k}", o, pts, h_cream, length=(3.0, 5.5), radius=0.2, tilt=60, seed=710 + k)
    return sp
