"""Put the Blender parts where gait.py's pose says they go."""
import math
import numpy as np
from mathutils import Vector, Matrix
import anatomy as A

UPV = Vector((0, 0, 1))


def frame(d, up=UPV):
    """A matrix whose Y axis runs along d and whose Z is as close to `up` as it can be."""
    y = Vector(d).normalized()
    x = y.cross(up)
    if x.length < 1e-4:
        x = Vector((1, 0, 0))
    x.normalize()
    z = x.cross(y)
    return Matrix((x, y, z)).transposed().to_4x4()


def at(m, origin):
    m = m.copy()
    m.translation = origin
    return m


def place(ob, p0, p1):
    ob.matrix_world = at(frame(Vector(p1) - Vector(p0)), Vector(p0))


def M4(a):
    return Matrix([list(map(float, r)) for r in a])


def apply_pose(sp, P):
    ctm = M4(P["ct"])
    sp.ct.matrix_world = ctm
    st = P["body"]
    ax, ay, az = A.AB_ATTACH
    abm = ctm @ Matrix.Translation((ax, ay, az)) @ Matrix.Rotation(A.AB_TILT + st["ab_pitch"], 4, "X") @ Matrix.Rotation(st["ab_yaw"], 4, "Z")
    b = st["breath"]
    sp.ab.matrix_world = abm @ Matrix.Diagonal((b, b, b, 1.0))
    for (side, i), J in P["legs"].items():
        s = sp.legs[(side, i)]
        place(s["fem"], J["H"], J["K1"])
        place(s["pat"], J["K1"], J["K2"])
        place(s["tib"], J["K2"], J["A"])
        place(s["met"], J["A"], J["M"])
        place(s["tar"], J["M"], J["F"])
    for side in (-1, 1):
        d0 = Vector((side * -0.20, 0.86, -0.46)).normalized()
        base = ctm @ Vector((side * A.PALP_BASE[0], A.PALP_BASE[1], A.PALP_BASE[2]))
        pos = base
        flex = ((0.0, 0.0), (math.radians(-20), math.radians(side * 18)), (math.radians(-26), math.radians(side * 22)))
        cur = Matrix.Identity(3)
        for k, part in enumerate(sp.palps[side]):
            pp, py = P["palps"][side][k]
            fp, fy = flex[k]
            cur = cur @ Matrix.Rotation(fy + py, 3, "Z") @ Matrix.Rotation(fp + pp, 3, "X")
            dk = ctm.to_3x3() @ cur @ d0
            part.matrix_world = at(frame(dk), pos)
            pos = pos + dk * A.PALP_LEN[k]
        ch, fg = sp.chel[side]
        open_ = P.get("chel", 0.0)
        dch = (ctm.to_3x3() @ Vector((side * (-0.05 + 0.2 * open_), 0.30, -0.95))).normalized()
        ch.matrix_world = at(frame(dch), ctm @ Vector((side * 5.2, 31.0, -3.2)))
