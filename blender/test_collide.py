"""Do the legs ever pass through each other or through the body?  python test_collide.py

Each leg piece is a capsule (its axis and the radius at that point); two capsules of different legs that overlap are a collision,
and so is a capsule that sinks into the carapace or abdomen ellipsoid. Sampled over every strip.
"""
import math
import numpy as np
import anatomy as A
import gait as G

RAD = {"fem": 4.6, "pat": 3.6, "tib": 3.0, "met": 2.0, "tar": 1.2}      # a typical radius of each piece
SEG = (("fem", "H", "K1"), ("pat", "K1", "K2"), ("tib", "K2", "A"), ("met", "A", "M"), ("tar", "M", "F"))


def seg_dist(p0, p1, q0, q1):
    u, v, w = p1 - p0, q1 - q0, p0 - q0
    a, b, c, d, e = u @ u, u @ v, v @ v, u @ w, v @ w
    D = a * c - b * b
    sN, sD, tN, tD = D, D, D, D
    if D < 1e-9:
        sN, sD, tN, tD = 0.0, 1.0, e, c
    else:
        sN, tN = (b * e - c * d), (a * e - b * d)
        if sN < 0:
            sN, tN, tD = 0.0, e, c
        elif sN > sD:
            sN, tN, tD = sD, e + b, c
    if tN < 0:
        tN = 0.0
        sN, sD = (0.0, sD) if -d < 0 else ((sD, sD) if -d > a else (-d, a))
    elif tN > tD:
        tN = tD
        sN, sD = (0.0, sD) if (-d + b) < 0 else ((sD, sD) if (-d + b) > a else (-d + b, a))
    sc = 0.0 if abs(sN) < 1e-9 else sN / sD
    tc = 0.0 if abs(tN) < 1e-9 else tN / tD
    return float(np.linalg.norm(w + sc * u - tc * v))


worst = 0.0
worst_at = None
body_worst = 0.0
count = 0
for name, n in G.COUNTS.items():
    for k in range(0, n, 2):
        P = G.strip_pose(name, k)
        M = P["ct"]
        legs = P["legs"]
        items = []
        for (side, i), J in legs.items():
            for nm, a, b in SEG:
                items.append(((side, i, nm), J[a], J[b], RAD[nm] * (0.92 if i == 3 else 1.0)))
        for x in range(len(items)):
            for y in range(x + 1, len(items)):
                (s1, i1, n1), a0, a1, r1 = items[x]
                (s2, i2, n2), b0, b1, r2 = items[y]
                if (s1, i1) == (s2, i2):
                    continue
                gap = seg_dist(a0, a1, b0, b1) - (r1 + r2)
                if gap < worst:
                    worst, worst_at = gap, (name, k, (s1, i1, n1), (s2, i2, n2))
        # body ellipsoids: carapace (centre at the carapace origin) and the abdomen
        Mi = np.linalg.inv(M)
        for (side, i, nm), a0, a1, r in items:
            for t in np.linspace(0, 1, 7):
                p = a0 + (a1 - a0) * t
                q = (Mi @ np.append(p, 1.0))[:3] - np.array([0.0, 2.0, 0.0])
                f = math.sqrt((q[0] / 22.0) ** 2 + (q[1] / 31.0) ** 2 + (q[2] / 13.0) ** 2)
                inside = (1.0 - f) * 13.0 - r
                if inside > body_worst:
                    body_worst = inside
        count += 1
print(f"{count} poses; worst leg-leg interpenetration: {worst:.2f} BU  {worst_at}")
print(f"worst leg sunk into the carapace: {body_worst:.2f} BU")
