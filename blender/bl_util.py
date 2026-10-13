"""Helpers for building the spider in Blender: colours, shader nodes, lofted meshes, tubes, and strands of hair."""
import math, random, bisect
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix


# ------------------------------------------------------------------------------------------------ colour
def lin1(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb(r, g, b, a=1.0):
    """sRGB 0..255 -> the linear RGBA Blender wants."""
    return (lin1(r), lin1(g), lin1(b), a)


def hexc(h, a=1.0):
    h = h.lstrip("#")
    return rgb(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


# ------------------------------------------------------------------------------------------------ interpolation
def pchip(xs, ys):
    """Monotone cubic through (xs, ys): no overshoot, so a profile table cannot ring."""
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    h = np.diff(xs); d = np.diff(ys) / h
    m = np.zeros(len(xs))
    m[1:-1] = (d[:-1] + d[1:]) / 2
    m[0], m[-1] = d[0], d[-1]
    for k in range(len(d)):
        if d[k] == 0:
            m[k] = m[k + 1] = 0
        else:
            a, b = m[k] / d[k], m[k + 1] / d[k]
            s = a * a + b * b
            if s > 9:
                t = 3 / math.sqrt(s)
                m[k], m[k + 1] = t * a * d[k], t * b * d[k]

    def f(x):
        x = np.asarray(x, float)
        i = np.clip(np.searchsorted(xs, x) - 1, 0, len(xs) - 2)
        t = (x - xs[i]) / h[i]
        h00 = (1 + 2 * t) * (1 - t) ** 2; h10 = t * (1 - t) ** 2; h01 = t * t * (3 - 2 * t); h11 = t * t * (t - 1)
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------------------------------------ meshes
def _se(th, n):
    c, s = math.cos(th), math.sin(th)
    e = 2.0 / n
    return math.copysign(abs(c) ** e, c), math.copysign(abs(s) ** e, s)


def loft(name, secs, sides=20, displace=None):
    """secs: (y, half width, top, bottom, superellipse n, cx, cz) rings along +Y, closed with a fan at each end.
    displace(x, y, z) -> dz lets the caller dent or raise the surface before smoothing."""
    bm = bmesh.new()
    rings = []
    for (y, wx, zt, zb, n, cx, cz) in secs:
        ring = []
        for k in range(sides):
            ux, uz = _se(2 * math.pi * k / sides, n)
            x, z = cx + wx * ux, cz + (zt * uz if uz >= 0 else zb * uz)
            if displace is not None:
                z += displace(x, y, z)
            ring.append(bm.verts.new((x, y, z)))
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


def tube_secs(L, prof, rings=20, flat=0.94, ball0=True, ball1=True, bend=None, sides_n=2.0):
    """Sections for a tube from y = 0 to y = L whose radius follows prof(t), with a ball at either end centred on the joint (so
    neighbouring pieces overlap like a ball joint). bend(t) -> (cx, cz) curves the axis."""
    bend = bend or (lambda t: (0.0, 0.0))
    secs = []
    r0, r1 = float(prof(0.0)), float(prof(1.0))
    if ball0:
        for a in (0.30, 0.70, 1.08, 1.40):
            cx, cz = bend(0.0)
            secs.append((-r0 * math.cos(a), r0 * math.sin(a), r0 * math.sin(a) * flat, r0 * math.sin(a) * flat, sides_n, cx, cz))
    for i in range(rings + 1):
        t = i / rings
        r = float(prof(t))
        cx, cz = bend(t)
        secs.append((L * t, r, r * flat, r * flat, sides_n, cx, cz))
    if ball1:
        for a in (1.40, 1.08, 0.70, 0.30):
            cx, cz = bend(1.0)
            secs.append((L + r1 * math.cos(a), r1 * math.sin(a), r1 * math.sin(a) * flat, r1 * math.sin(a) * flat, sides_n, cx, cz))
    return secs


def cone_mesh(name, L, r0, r1, bend=0.0, sides=10, rings=8):
    """A tapered, optionally curved spike from y = 0 to L (bend: sideways -z offset at the tip)."""
    secs = []
    for i in range(rings + 1):
        t = i / rings
        r = r0 + (r1 - r0) * t
        secs.append((L * t, max(r, 0.04), max(r, 0.04), max(r, 0.04), 2.0, 0.0, -bend * t * t))
    return loft(name, secs, sides)


def add_obj(name, me, mat=None, subsurf=(1, 2), parent=None, collection=None):
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    if subsurf:
        m = ob.modifiers.new("sub", "SUBSURF")
        m.levels, m.render_levels = subsurf
    if parent is not None:
        ob.parent = parent
        ob.matrix_parent_inverse = Matrix.Identity(4)
    return ob


def sphere_mesh(name, r, seg=24, rings=14):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


# ------------------------------------------------------------------------------------------------ shader nodes
def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, m.node_tree


def N(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def L(nt, a, b):
    nt.links.new(a, b)


def math_node(nt, op, a=None, b=None, c=None):
    n = N(nt, "ShaderNodeMath", operation=op)
    for k, v in enumerate((a, b, c)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[k].default_value = v
        else:
            L(nt, v, n.inputs[k])
    return n.outputs[0]


def object_axis(nt, axis, scale, offset=0.0):
    """Object-space coordinate along an axis, (value + offset) / scale."""
    tc = N(nt, "ShaderNodeTexCoord")
    sp = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, tc.outputs["Object"], sp.inputs[0])
    v = sp.outputs[axis]
    if offset:
        v = math_node(nt, "ADD", v, offset)
    return math_node(nt, "MULTIPLY", v, 1.0 / scale), tc


def banded_color(nt, t, bands, warp=0.0, noise_scale=3.0, tc=None, soft=0.0):
    """bands = [(t_end, rgba)] along t in [0, 1]. Hard steps, or with `soft` a blend of half-width soft either side of each
    boundary. A little noise in t keeps the edges from being ruler-straight."""
    if warp:
        tc = tc or N(nt, "ShaderNodeTexCoord")
        nz = N(nt, "ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = noise_scale, 3.0
        L(nt, tc.outputs["Object"], nz.inputs[0])
        off = math_node(nt, "MULTIPLY_ADD", nz.outputs["Fac"], warp * 2, -warp)
        t = math_node(nt, "ADD", t, off)
    ramp = N(nt, "ShaderNodeValToRGB")
    cr = ramp.color_ramp
    els = cr.elements
    if soft:
        cr.interpolation = "LINEAR"
        stops, start, last = [], 0.0, len(bands) - 1
        for k, (te, col) in enumerate(bands):
            a = start + (soft if k > 0 else 0.0)
            bpos = te - (soft if k < last else 0.0)
            bpos = max(bpos, a + 1e-3)
            stops.append((a if k > 0 else 0.0, col))
            stops.append((bpos if k < last else 1.0, col))
            start = te
        while len(els) < len(stops):
            els.new(0.5)
        for k, (pos, col) in enumerate(stops):
            els[k].position = min(pos, 1.0)
            els[k].color = col
    else:
        cr.interpolation = "CONSTANT"
        prev = 0.0
        for k, (te, col) in enumerate(bands):
            if k >= len(els):
                els.new(prev)
            els[k].position = prev
            els[k].color = col
            prev = te
    L(nt, t, ramp.inputs[0])
    return ramp.outputs[0]


def mix_rgba(nt, fac, a, b):
    m = N(nt, "ShaderNodeMix")
    m.data_type = "RGBA"
    if isinstance(fac, (int, float)):
        m.inputs[0].default_value = fac
    else:
        L(nt, fac, m.inputs[0])
    for idx, v in ((6, a), (7, b)):
        if isinstance(v, tuple):
            m.inputs[idx].default_value = v
        else:
            L(nt, v, m.inputs[idx])
    return m.outputs[2]


# ------------------------------------------------------------------------------------------------ hair
def surface_points(ob, n, accept=None, seed=1, weight=None):
    """n (position, normal) samples on the evaluated surface of ob, in its local space, area-weighted; accept(p, nrm) -> a
    probability thins them into a pattern; weight(p, nrm) -> relative density (also thins)."""
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
    pts = []
    guard = 0
    while len(pts) < n and guard < n * 60:
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
    area = tot
    ev.to_mesh_clear()
    return pts


def surface_area(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    co = [v.co for v in me.vertices]
    tot = sum(((co[t.vertices[1]] - co[t.vertices[0]]).cross(co[t.vertices[2]] - co[t.vertices[0]])).length * 0.5 for t in me.loop_triangles)
    ev.to_mesh_clear()
    return tot


def mirror_x(pts):
    return [(Vector((-p.x, p.y, p.z)), Vector((-n.x, n.y, n.z))) for p, n in pts]


def make_hair(name, parent, pts, mat, length=(4.0, 7.0), radius=0.22, tilt=62.0, flow=(0.0, 1.0, 0.0), curl=0.55, jitter=14.0,
              straight=False, seed=3, tip=0.25, sink=0.5, points=3):
    """One Curves object of strands rooted at pts, growing along the surface normal and bending toward `flow`.
    `points` control points per strand (3 is plenty at this size; 4 for long bristles)."""
    r = random.Random(seed)
    cu = bpy.data.hair_curves.new(name)
    n = len(pts)
    if n == 0:
        return None
    cu.add_curves([points] * n)
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
        seg = ln / (points - 1)
        cur = p - nrm * sink
        pos += [*cur]
        rad += [radius]
        dirv = (nrm * 0.75 + d * 0.25).normalized()
        for k in range(1, points):
            if straight:
                dirv = d
            else:
                bend = curl * (k / (points - 1))
                dirv = (dirv * (1 - 0.35) + (d * (1 - bend) + t * bend * 0.9 + nrm * 0.1).normalized() * 0.35).normalized() if k > 1 else dirv
            cur = cur + dirv * seg
            pos += [*cur]
            f = k / (points - 1)
            rad += [radius * (1.0 - f * (1.0 - tip))]
    cu.points.foreach_set("position", pos)
    cu.points.foreach_set("radius", rad)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.matrix_parent_inverse = Matrix.Identity(4)
    cu.materials.append(mat)
    return ob
