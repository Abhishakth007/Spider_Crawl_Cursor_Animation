"""Posing and walking the spider from code.

No armature: each rigid part is placed by hand, the way a rig would, and the fur follows as children.

  solve_leg      three rigid parts, hip -> knee -> ankle -> foot. The foot is a target; the metatarsus keeps a set slope,
                 which fixes the ankle; the knee is the one point that is the right distance from hip and ankle, on the side
                 the pole points to. Legs 1 and 2 bow their knees forward, 3 and 4 back.
  gait_pose      one point in a gait cycle. The legs walk as two alternating tetrapods (L1 R2 L3 R4 against R1 L2 R3 L4),
                 each foot on the ground 60 % of the time. A foot that is down is planted: in the spider's own frame it
                 slides by exactly what the body travels, so played at the right speed it never skates. `theta` mixes the
                 gait: 0 walks straight, 90 pivots on the spot, in between curves.
  idle_pose      the stance the gait stops in (all eight feet down), with a breath, a twitch of the palps, a sway of the abdomen.
"""
import math
from mathutils import Vector, Matrix
import spider_model as M

UP = Vector((0, 0, 1))
BETA = 0.60                  # share of the cycle a foot is on the ground
STRIDE = 84.0                # body travel per cycle when walking straight (BU)
TURN = math.radians(48.0)    # body rotation per cycle when pivoting
LIFT = 15.0
FOOT_R = 1.0
LEG_ANGLE = {1: 34.0, 2: 76.0, 3: 106.0, 4: 143.0}     # from straight ahead, outward
LEG_REACH = {1: 104.0, 2: 108.0, 3: 106.0, 4: 112.0}   # hip to foot, along the ground
META_ELEV = {1: 62.0, 2: 66.0, 3: 66.0, 4: 62.0}      # slope of the metatarsus
POLE_TILT = {1: 24.0, 2: 36.0, 3: -34.0, 4: -50.0}     # knee's sideways lean off the vertical (+ forward, - back)
TETRA_A = {(-1, 1), (1, 2), (-1, 3), (1, 4)}


def frame(d, up=UP):
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


def rot(pitch=0.0, roll=0.0, yaw=0.0):
    return Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(roll, 4, "Y") @ Matrix.Rotation(pitch, 4, "X")


def neutral_foot(side, i):
    hx, hy = M.HIPS[i]
    a = math.radians(LEG_ANGLE[i])
    R = LEG_REACH[i]
    return Vector((side * (hx + R * math.sin(a)), hy + R * math.cos(a), FOOT_R))


def solve_leg(H, F, lens, elev, tilt):
    """-> knee, ankle (world). Reach is clamped, so a target out of range stretches toward it instead of failing."""
    a, b, c = lens
    h = Vector((F.x - H.x, F.y - H.y, 0.0))
    rhat = h.normalized() if h.length > 1e-6 else Vector((1, 0, 0))
    el = math.radians(elev)
    ankle = F + c * (-math.cos(el) * rhat + math.sin(el) * UP)
    d = ankle - H
    dl = d.length
    lo, hi = abs(a - b) + 1e-3, a + b - 1e-3
    if dl > hi:
        ankle = H + d * (hi / dl); dl = hi; d = ankle - H
    elif dl < lo:
        ankle = H + d * (lo / dl); dl = lo; d = ankle - H
    x = (a * a - b * b + dl * dl) / (2 * dl)
    hgt = math.sqrt(max(a * a - x * x, 0.0))
    dhat = d / dl
    t = Vector((-rhat.y, rhat.x, 0.0))
    if t.y < 0:
        t = -t
    tl = math.radians(tilt)
    pole = UP * math.cos(tl) + t * math.sin(tl)
    perp = pole - dhat * pole.dot(dhat)
    perp = perp.normalized() if perp.length > 1e-6 else UP
    knee = H + dhat * x + perp * hgt
    return knee, ankle


def smooth(q):
    return q * q * (3 - 2 * q)


def foot_track(side, i, phase, theta, tetra_offset):
    """Foot target in the spider's frame at this point of the cycle -> (Vector, planted?)."""
    a, b = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    N = neutral_foot(side, i)
    u = (phase + tetra_offset + 0.45) % 1.0
    sw = 1.0 - BETA

    def planted(s):
        d = BETA * STRIDE * a * (s - 0.5)
        psi = BETA * TURN * b * (s - 0.5)
        v = Vector((N.x, N.y - d))
        c, sn = math.cos(-psi), math.sin(-psi)
        return Vector((v.x * c - v.y * sn, v.x * sn + v.y * c, FOOT_R))

    if u >= sw:
        return planted((u - sw) / BETA), True
    q = u / sw
    p0, p1 = planted(1.0), planted(0.0)
    e = smooth(q)
    # the foot swings outward a touch as it comes round, and lifts in an arc that peaks a little before the middle
    lift = LIFT * math.sin(math.pi * q ** 0.85) ** 1.1
    p = p0 + (p1 - p0) * e
    out = Vector((p.x - 0, 0, 0)).normalized() * (3.0 * math.sin(math.pi * q)) if abs(p.x) > 1e-6 else Vector()
    return Vector((p.x + out.x, p.y, FOOT_R + lift)), False


def gait_pose(phase, theta=0.0, speed_mix=1.0):
    """The whole spider at `phase` (0..1) of the cycle -> a pose dict for apply_pose."""
    TAU = 2 * math.pi
    s_b = math.sin(math.radians(theta))
    sway_x = 1.5 * math.sin(TAU * phase + 0.8)
    yaw = math.radians(2.8) * math.sin(TAU * phase) + math.radians(9.0) * s_b       # the head leads into a turn
    roll = math.radians(1.6) * math.sin(TAU * phase + 0.4) - math.radians(3.5) * s_b      # lean into a turn
    pitch = math.radians(0.7) * math.cos(2 * TAU * phase)
    bob = -0.8 * math.cos(2 * TAU * phase) - 0.6
    pose = {
        "ct": (Vector((sway_x, 0.0, bob)), pitch, roll, yaw),
        # the abdomen trails: it lags the carapace's own sway, and swings out the far side of a turn
        "ab": (math.radians(2.0) * math.cos(2 * TAU * phase - 1.2),
               -1.7 * (yaw - math.radians(9.0) * s_b) - math.radians(2.0) * math.sin(TAU * phase - 1.0) - math.radians(19.0) * s_b, 1.0),
        "feet": {}, "planted": {},
    }
    for side in (-1, 1):
        for i in (1, 2, 3, 4):
            off = 0.0 if (side, i) in TETRA_A else 0.5
            F, pl = foot_track(side, i, phase, theta, off)
            pose["feet"][(side, i)] = F
            pose["planted"][(side, i)] = pl
    pose["palps"] = palp_motion(phase * 2.0, 1.0, "walk")
    pose["chel"] = 0.0
    return pose


def palp_motion(t, amp, mode="idle"):
    """Palps twitch a little all the time (t in cycles; periodic, so a loop closes)."""
    TAU = 2 * math.pi
    out = {}
    for side in (-1, 1):
        ph = 0.0 if side < 0 else 0.37
        out[side] = [
            (math.radians(5.0) * amp * math.sin(TAU * (t + ph)), math.radians(6.0) * amp * math.sin(TAU * (2 * t + ph + 0.2))),
            (math.radians(8.0) * amp * math.sin(TAU * (2 * t + ph + 0.5)), math.radians(4.0) * amp * math.sin(TAU * (t + ph + 0.1))),
            (math.radians(10.0) * amp * math.sin(TAU * (3 * t + ph)), math.radians(3.0) * amp * math.sin(TAU * (t + ph + 0.4))),
        ]
    return out


def apply_pose(sp, pose):
    """Place every rigid part. Children (fur, eyes, claws, fangs, spinnerets) ride along."""
    loc, pitch, roll, yaw = pose["ct"]
    ctm = Matrix.Translation(Vector((0, 0, M.CT_Z)) + loc) @ rot(pitch, roll, yaw)
    sp.ct.matrix_world = ctm
    ap, ay, breath = pose["ab"]
    abm = ctm @ Matrix.Translation(M.AB_ATTACH) @ rot(M.AB_TILT + ap, 0.0, ay)
    abm = abm @ Matrix.Diagonal((breath, breath, breath, 1.0))
    sp.ab.matrix_world = abm
    for side in (-1, 1):
        for i in (1, 2, 3, 4):
            hx, hy = M.HIPS[i]
            H = ctm @ Vector((side * hx, hy, M.HIP_Z - M.CT_Z))
            F = pose["feet"][(side, i)]
            lens = sp.leg_len[i]
            knee, ankle = solve_leg(H, F, lens, META_ELEV[i], POLE_TILT[i])
            segs = sp.legs[(side, i)]
            segs[0].matrix_world = at(frame(knee - H), H)
            segs[1].matrix_world = at(frame(ankle - knee), knee)
            segs[2].matrix_world = at(frame(F - ankle), ankle)
        # palps: three parts, each turning a little more
        d0 = Vector((side * -0.20, 0.86, -0.46)).normalized()
        P = ctm @ Vector((side * 8.2, 23.5, -4.4))
        m = ctm.to_3x3().to_4x4()
        direction = ctm.to_3x3() @ d0
        pos = P
        base_len = (11.0, 9.0, 8.0)
        flex = ((0.0, 0.0), (math.radians(-20), math.radians(side * 18)), (math.radians(-26), math.radians(side * 22)))
        cur = Matrix.Identity(3)
        for k, part in enumerate(sp.palps[side]):
            pp, py = pose["palps"][side][k]
            fp, fy = flex[k]
            cur = cur @ Matrix.Rotation(fy + py, 3, "Z") @ Matrix.Rotation(fp + pp, 3, "X")
            dk = ctm.to_3x3() @ cur @ d0
            part.matrix_world = at(frame(dk), pos)
            pos = pos + dk * base_len[k]
        ch, fg = sp.chel[side]
        open_ = pose.get("chel", 0.0)
        dch = (ctm.to_3x3() @ Vector((side * (-0.05 + 0.2 * open_), 0.30, -0.95))).normalized()
        ch.matrix_world = at(frame(dch), ctm @ Vector((side * 6.0, 24.0, -1.6)))


# ------------------------------------------------------------------------------------------ the strips
# Every strip is a loop of `count` frames. The walks are indexed by gait phase; the idles all begin and end on the pose
# the walk stops in (phase 0 of the straight gait), so the page can drop from a walk into any of them and back without a pop.
WALKS = {"walk0": 0.0, "walk18": 18.0, "walk34": 34.0, "walk50": 50.0, "walk70": 70.0, "pivot": 90.0}
COUNTS = {"walk0": 32, "walk18": 32, "walk34": 32, "walk50": 32, "walk70": 32, "pivot": 32,
          "idle_calm": 48, "idle_wave": 60, "idle_tap": 44, "idle_groom": 52}


def _env(t, a=0.0, b=1.0):
    """0 at both ends of [a, b], 1 through the middle, smooth."""
    if t <= a or t >= b:
        return 0.0
    u = (t - a) / (b - a)
    return math.sin(math.pi * u) ** 2


def idle_pose(kind, t):
    """t in [0, 1): one loop. Starts and ends on the walk's rest pose."""
    TAU = 2 * math.pi
    pose = gait_pose(0.0, 0.0)
    loc, pitch, roll, yaw = pose["ct"]
    ap, ay, breath = pose["ab"]
    br = math.sin(TAU * t)
    pose["ct"] = (loc + Vector((0, 0, 0.32 * br)), pitch, roll, yaw)
    pose["ab"] = (ap + math.radians(0.9) * br, ay + math.radians(1.3) * math.sin(TAU * t + 0.6) - math.radians(1.3) * math.sin(0.6),
                  breath * (1 + 0.013 * br))
    pose["palps"] = palp_motion(t, 1.0)
    L1, L4 = (-1, 1), (-1, 4)
    if kind == "wave":
        e = _env(t, 0.05, 0.95)
        base = pose["feet"][L1]
        w = math.sin(TAU * 3.0 * (t - 0.05))
        pose["feet"][L1] = base + Vector((-14.0 * e + 17.0 * e * w, 22.0 * e, 34.0 * e + 4.0 * e * math.cos(TAU * 3.0 * (t - 0.05))))
        pose["planted"][L1] = False
        pose["palps"] = palp_motion(t, 1.0 + 0.8 * e)
    elif kind == "tap":
        # a rear leg lifts and taps twice, the abdomen rocks with it
        e = _env(t, 0.08, 0.92)
        base = pose["feet"][L4]
        tap = max(0.0, math.sin(TAU * 2.0 * (t - 0.08))) ** 1.5
        pose["feet"][L4] = base + Vector((-12.0 * e, 6.0 * e + 7.0 * e * tap, 12.0 * e + 9.0 * e * tap))
        pose["planted"][L4] = False
        ap, ay, bb = pose["ab"]
        pose["ab"] = (ap + math.radians(2.4) * e * math.sin(TAU * 2.0 * (t - 0.08)), ay, bb)
    elif kind == "groom":
        # both palps rub the fangs: bigger, quicker palp motion, the chelicerae working
        e = _env(t, 0.06, 0.94)
        pa = palp_motion(t * 4.0, 1.0)
        for side in (-1, 1):
            for k in range(3):
                p0, y0 = pose["palps"][side][k]
                p1, y1 = pa[side][k]
                pose["palps"][side][k] = (p0 + (math.radians(34 - 12 * k) * 1.0 + p1 * 3.0) * e, y0 + (-side * math.radians(24 - 6 * k) + y1 * 3.0) * e)
        pose["chel"] = 0.55 * e * (0.5 + 0.5 * math.sin(TAU * 4.0 * t))
    return pose


def strip_pose(name, k):
    n = COUNTS[name]
    if name in WALKS:
        return gait_pose(k / n, WALKS[name])
    return idle_pose(name.split("_", 1)[1], k / n)
