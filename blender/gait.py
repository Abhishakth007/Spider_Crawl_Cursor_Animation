"""The walk, from the reference. Pure maths (numpy): no Blender in here, so it can be tested on its own.

    pose(phase, theta)  one instant of the gait cycle -> every joint of the spider, in the spider's frame
    idle_pose(kind, t)  the stance the gait stops in, breathing, plus a fidget

What the reference walk cycle does, and so what this does:
  - two alternating tetrapods, L1 R2 L3 R4 against R1 L2 R3 L4, each planted a little over half the cycle, so there is always
    a moment (phase 0 and 0.5) with all eight feet down;
  - the legs of a tetrapod move together, the rear two a hair ahead of the front two;
  - a planted foot is fixed in the world: in the spider's own frame it slides back by exactly what the body travels, so played
    at the right speed it cannot skate. That holds on arcs too: the body is moved as a rigid body along a circle;
  - a swinging foot is eased through the world between where it lifted and where it lands, then expressed in the spider's frame;
    it clears the ground in an arch that peaks early, and bows outward as it comes round;
  - the body carries on almost rigidly, with a small bob at twice the step rate, a little roll and yaw, and an abdomen that lags.

`theta` blends the gait: 0 walks straight, 90 pivots on the spot, between them curves (positive turns left, seen from above).
"""
import math
import numpy as np
import anatomy as A

TAU = 2 * math.pi
UP = np.array([0.0, 0.0, 1.0])


def V(x=0.0, y=0.0, z=0.0):
    return np.array([x, y, z], float)


def unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def Rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def Rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1.0, 0, 0], [0, c, -s], [0, s, c]])


def Ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1.0, 0], [-s, 0, c]])


def smootherstep(q):
    q = min(1.0, max(0.0, q))
    return q * q * q * (q * (6 * q - 15) + 10)


# -------------------------------------------------------------------------------------------------- the stance
def hip_local(side, i):
    hx, hy = A.HIPS[i]
    return V(side * hx, hy, A.HIP_Z - A.CT_Z)


def neutral_foot(side, i):
    hx, hy = A.HIPS[i]
    a = math.radians(A.FOOT_ANGLE[i])
    R = A.FOOT_REACH[i]
    return V(side * (hx + R * math.sin(a)), hy + R * math.cos(a), A.FOOT_R)


PIV_Y = float(np.mean([neutral_foot(s, i)[1] for s in (-1, 1) for i in (1, 2, 3, 4)]))   # the middle of the feet
PIV = V(0.0, PIV_Y, 0.0)


# -------------------------------------------------------------------------------------------------- a leg
def side_of(H):
    return 1.0 if H[0] >= 0 else -1.0


def solve_leg(H, F, i, knee_elev=None, elev=None):
    """Joints of one leg for a hip H and a foot F (world / spider frame). Returns dict H K1 K2 A M F (numpy) and `stretch`."""
    L = A.LEG[i]
    a, b, c = A.chords(i)
    kelev = math.radians(A.KNEE_ELEV[i] if knee_elev is None else knee_elev)
    elev0 = math.radians(A.META_ELEV[i] if elev is None else elev)
    h = V(F[0] - H[0], F[1] - H[1], 0.0)
    rho = np.linalg.norm(h)
    rhat = h / rho if rho > 1e-6 else V(1, 0, 0)
    lo, hi = abs(a - b) + 4.0, a + b - 1.5

    def ankle(el):
        return F + c * (-math.cos(el) * rhat + math.sin(el) * UP)

    el = elev0
    dl = np.linalg.norm(ankle(el) - H)
    if dl > hi or dl < lo:
        # a steeper or shallower foot brings the ankle back into reach: take the slope nearest the wanted one that does
        best = None
        for deg in np.arange(20.0, 88.0, 0.5):
            e = math.radians(deg)
            d = np.linalg.norm(ankle(e) - H)
            if lo <= d <= hi and (best is None or abs(e - elev0) < abs(best - elev0)):
                best = e
        if best is not None:
            el = best
    Apt = ankle(el)
    d = Apt - H
    dl = float(np.linalg.norm(d))
    stretch = False
    if dl > hi:
        Apt = H + d * (hi / dl); dl = hi; d = Apt - H; stretch = True
    elif dl < lo:
        Apt = H + d * (lo / dl); dl = lo; d = Apt - H; stretch = True
    dhat = d / dl
    x = (a * a - b * b + dl * dl) / (2 * dl)
    hgt = math.sqrt(max(a * a - x * x, 0.0))
    # the knee lies on a circle around the hip-ankle line; take the point where the femur rises at the wanted angle. That point
    # is out of the leg's vertical plane (the spider's bowed elbow); it bows toward the side this leg prefers.
    e1 = UP - dhat * float(UP @ dhat)
    e1 = unit(e1) if np.linalg.norm(e1) > 1e-6 else UP
    e2 = np.cross(dhat, e1)
    C = H + dhat * x
    den = hgt * float(e1[2])
    cth = 1.0
    if abs(den) > 1e-6:
        cth = max(-1.0, min(1.0, (a * math.sin(kelev) - float(C[2] - H[2])) / den))
    cth = min(cth, math.cos(math.radians(A.KNEE_TILT[i])))
    sth = math.sqrt(1.0 - cth * cth)
    # e2 mirrors with a sign flip, so the bow side is a fixed per-leg choice times the side (no flipping from frame to frame)
    sgn = float(A.KNEE_SIDE[i]) * side_of(H)
    K1 = C + hgt * (cth * e1 + sgn * sth * e2)
    # patella-tibia: the chord K1 -> A is bent (convex upward) into the two real pieces
    K2 = _bend(K1, Apt, L["pat"], L["tib"])
    M = _bend(Apt, F, L["met"], L["tar"])
    return dict(H=H, K1=K1, K2=K2, A=Apt, M=M, F=F, stretch=stretch, elev=el)


def _bend(P0, P1, l0, l1):
    """Joint J with |P0 J| = l0 and |J P1| = l1, on the upper side of the chord."""
    ch = P1 - P0
    c = float(np.linalg.norm(ch))
    chat = ch / c
    cosa = (l0 * l0 + c * c - l1 * l1) / (2 * l0 * c)
    cosa = max(-1.0, min(1.0, cosa))
    sina = math.sqrt(1 - cosa * cosa)
    n = UP - chat * float(UP @ chat)
    n = unit(n) if np.linalg.norm(n) > 1e-6 else UP
    return P0 + l0 * (cosa * chat + sina * n)


# -------------------------------------------------------------------------------------------------- the body's path
def _arc(t, v, w):
    """Where the body is after time t (cycles), relative to where it was, moving v per cycle and turning w rad per cycle:
    a point (x, y) and a heading angle. Heading 0 is +Y, positive turns left (counter-clockwise)."""
    al = w * t
    if abs(w) < 1e-6:
        return V(0.0, v * t, 0.0), al
    R = v / w
    return V(-R * (1 - math.cos(al)), R * math.sin(al), 0.0), al


def _to_body(W, t, v, w):
    """A point fixed in the world (given in the frame the body had at t = 0) -> the body's frame at time t."""
    T, al = _arc(t, v, w)
    return Rz(-al) @ (W - T)


def _to_world(p, t, v, w):
    T, al = _arc(t, v, w)
    return T + Rz(al) @ p


def foot_track(side, i, phase, theta, extra_lift=0.0):
    """Foot target in the spider's frame -> (point, planted?, swing fraction q or None, lift)."""
    th = math.radians(theta)
    a, b = math.cos(th), math.sin(th)
    v, w = A.STRIDE * a, A.TURN * b
    off = 0.0 if (side, i) in A.TETRA_A else 0.5
    tau = (phase - off - A.LAG[i]) % 1.0
    beta, sw, dl = A.BETA, 1.0 - A.BETA, A.DELTA
    N = neutral_foot(side, i)
    n0 = N - PIV

    def planted(s):
        # fixed in the world, with its mid-stance at the neutral place
        T_mid, al_mid = _arc(beta * 0.5, v, w)
        W_td = T_mid + Rz(al_mid) @ n0
        p = _to_body(W_td, beta * s, v, w)
        return p + PIV

    t_swing0 = 0.5 + dl                         # swing runs from here to 1 - dl
    if tau >= 1.0 - dl or tau < t_swing0:
        s = ((tau - (1.0 - dl)) % 1.0) / beta
        p = planted(min(1.0, max(0.0, s)))
        p[2] = A.FOOT_R
        return p, True, None, 0.0
    q = (tau - t_swing0) / sw
    p0, p1 = planted(1.0) - PIV, planted(0.0) - PIV          # lift-off and touch-down, in the body frame of their own moments
    W1 = _to_world(p1, sw, v, w)
    e = smootherstep(q)
    W = p0 + (W1 - p0) * e
    p = _to_body(W, q * sw, v, w) + PIV
    lift = math.sin(math.pi * q ** 0.8) ** 1.15
    hx, hy = A.HIPS[i]
    out = unit(V(N[0] - side * hx, N[1] - hy, 0.0))
    p = p + out * (A.BULGE[i] * math.sin(math.pi * q))
    p[2] = A.FOOT_R + (A.LIFT[i] + extra_lift) * lift
    return p, False, q, lift


# -------------------------------------------------------------------------------------------------- the body
def palp_motion(t, amp=1.0):
    """The palps never keep still: a few small periodic nods and sweeps (t in cycles, so a loop closes)."""
    out = {}
    for side in (-1, 1):
        ph = 0.0 if side < 0 else 0.37
        out[side] = [
            (math.radians(5.0) * amp * math.sin(TAU * (t + ph)), math.radians(6.0) * amp * math.sin(TAU * (2 * t + ph + 0.2))),
            (math.radians(8.0) * amp * math.sin(TAU * (2 * t + ph + 0.5)), math.radians(4.0) * amp * math.sin(TAU * (t + ph + 0.1))),
            (math.radians(10.0) * amp * math.sin(TAU * (3 * t + ph)), math.radians(3.0) * amp * math.sin(TAU * (t + ph + 0.4))),
        ]
    return out


def body_state(phase, theta):
    s_b = math.sin(math.radians(theta))
    yaw = math.radians(2.6) * math.sin(TAU * phase) + math.radians(9.0) * s_b      # the head leads into a turn
    roll = math.radians(1.5) * math.sin(TAU * phase + 0.4) - math.radians(3.5) * s_b
    pitch = math.radians(0.8) * math.cos(2 * TAU * phase)
    sway = 1.3 * math.sin(TAU * phase + 0.8)
    bob = -0.9 * math.cos(2 * TAU * phase) - 0.5
    return dict(
        pos=V(sway, 0.0, bob), pitch=pitch, roll=roll, yaw=yaw,
        # the abdomen trails: it lags the carapace's own sway and swings out the far side of a turn
        ab_pitch=math.radians(2.0) * math.cos(2 * TAU * phase - 1.2),
        ab_yaw=-1.7 * (yaw - math.radians(9.0) * s_b) - math.radians(2.0) * math.sin(TAU * phase - 1.0) - math.radians(19.0) * s_b,
        breath=1.0)


def carapace_matrix(st):
    """4x4 of the carapace for a body_state."""
    R = Rz(st["yaw"]) @ Ry(st["roll"]) @ Rx(st["pitch"])
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = V(0, 0, A.CT_Z) + st["pos"]
    return M


def pose(phase, theta=0.0, foot_override=None, extra=None):
    """The whole spider at `phase` (0..1) of the cycle. foot_override: {(side, i): (point, planted)} for fidgets."""
    st = body_state(phase, theta)
    M = carapace_matrix(st)
    P = dict(body=st, ct=M, legs={}, feet={}, planted={}, lift={})
    for side in (-1, 1):
        for i in (1, 2, 3, 4):
            F, planted, q, lift = foot_track(side, i, phase, theta)
            if foot_override and (side, i) in foot_override:
                F, planted = foot_override[(side, i)]
            H = (M @ np.append(hip_local(side, i), 1.0))[:3]
            P["legs"][(side, i)] = solve_leg(H, F, i, elev=math.degrees(math.radians(A.META_ELEV[i]) - A.FLEX * lift))
            P["feet"][(side, i)] = F
            P["planted"][(side, i)] = planted
            P["lift"][(side, i)] = lift
    P["palps"] = palp_motion(phase * 2.0, 1.0)
    P["chel"] = 0.0
    return P


# -------------------------------------------------------------------------------------------------- the strips
WALKS = {"walk0": 0.0, "walk18": 18.0, "walk34": 34.0, "walk50": 50.0, "walk70": 70.0, "pivot": 90.0}
COUNTS = {"walk0": 32, "walk18": 32, "walk34": 32, "walk50": 32, "walk70": 32, "pivot": 32,
          "idle_calm": 48, "idle_wave": 60, "idle_tap": 44, "idle_groom": 52, "idle_rock": 56}


def _env(t, a=0.0, b=1.0):
    if t <= a or t >= b:
        return 0.0
    u = (t - a) / (b - a)
    return math.sin(math.pi * u) ** 2


def idle_pose(kind, t):
    """t in [0, 1): one loop, starting and ending on the walk's rest pose (phase 0 of the straight gait)."""
    br = math.sin(TAU * t)
    over = {}
    base = pose(0.0, 0.0)
    L1, L4 = (-1, 1), (-1, 4)
    extra = {}
    if kind == "wave":
        # the front leg comes up and feels the air
        e = _env(t, 0.05, 0.95)
        w = math.sin(TAU * 3.0 * (t - 0.05))
        F0 = base["feet"][L1]
        extra[L1] = (F0 + V(-16.0 * e + 30.0 * e * w, 30.0 * e, 44.0 * e + 7.0 * e * math.cos(TAU * 3.0 * (t - 0.05))), False)
    elif kind == "tap":
        e = _env(t, 0.08, 0.92)
        tap = max(0.0, math.sin(TAU * 2.0 * (t - 0.08))) ** 1.5
        F0 = base["feet"][L4]
        extra[L4] = (F0 + V(-16.0 * e, 8.0 * e + 9.0 * e * tap, 16.0 * e + 12.0 * e * tap), False)
    P = pose(0.0, 0.0, foot_override=extra or None)
    # breathing and a slow weight shift
    st = P["body"]
    st["pos"] = st["pos"] + V(0, 0, 0.32 * br)
    st["ab_pitch"] += math.radians(0.9) * br
    st["ab_yaw"] += math.radians(1.3) * math.sin(TAU * t + 0.6) - math.radians(1.3) * math.sin(0.6)
    st["breath"] = 1.0 + 0.013 * br
    if kind == "tap":
        e = _env(t, 0.08, 0.92)
        st["ab_pitch"] += math.radians(2.4) * e * math.sin(TAU * 2.0 * (t - 0.08))
    P["ct"] = carapace_matrix(st)
    for side in (-1, 1):
        for i in (1, 2, 3, 4):
            F, pl = P["feet"][(side, i)], P["planted"][(side, i)]
            H = (P["ct"] @ np.append(hip_local(side, i), 1.0))[:3]
            P["legs"][(side, i)] = solve_leg(H, F, i, elev=math.degrees(math.radians(A.META_ELEV[i]) - A.FLEX * P["lift"][(side, i)]))
    if kind == "rock":
        e = _env(t, 0.04, 0.96)
        st["pos"] = st["pos"] + V(2.4 * e * math.sin(TAU * t), 0.0, 0.0)
        st["yaw"] += math.radians(3.2) * e * math.sin(TAU * t + 0.5)
        st["roll"] += math.radians(2.0) * e * math.sin(TAU * t)
        st["ab_yaw"] += -math.radians(4.0) * e * math.sin(TAU * t - 0.3)
        P["ct"] = carapace_matrix(st)
        for side in (-1, 1):
            for i in (1, 2, 3, 4):
                H = (P["ct"] @ np.append(hip_local(side, i), 1.0))[:3]
                P["legs"][(side, i)] = solve_leg(H, P["feet"][(side, i)], i)
    P["palps"] = palp_motion(t, 1.0)
    if kind == "wave":
        P["palps"] = palp_motion(t, 1.0 + 0.8 * _env(t, 0.05, 0.95))
    if kind == "groom":
        e = _env(t, 0.06, 0.94)
        pa = palp_motion(t * 4.0, 1.0)
        for side in (-1, 1):
            for k in range(3):
                p0, y0 = P["palps"][side][k]
                p1, y1 = pa[side][k]
                P["palps"][side][k] = (p0 + (math.radians(34 - 12 * k) + p1 * 3.0) * e, y0 + (-side * math.radians(24 - 6 * k) + y1 * 3.0) * e)
        P["chel"] = 0.55 * e * (0.5 + 0.5 * math.sin(TAU * 4.0 * t))
    return P


def strip_pose(name, k):
    n = COUNTS[name]
    if name in WALKS:
        return pose(k / n, WALKS[name])
    return idle_pose(name.split("_", 1)[1], k / n)
