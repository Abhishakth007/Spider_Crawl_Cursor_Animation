"""Tests for the gait maths:  python -I test_gait.py   (run from this folder)

 - every rigid piece of every leg keeps its length at every phase and every turn
 - no leg is asked to reach beyond what it can (the solver would have to stretch it)
 - a planted foot is fixed in the world (it does not skate), on straight walks, arcs and pivots
 - all eight feet are down at phase 0 and 0.5, which is where the page stops and starts the gait
 - the gait at phase+0.5 is the mirror image of the gait at phase (the page flips sprites to turn the other way)
 - feet never go through the ground; the tetrapods really alternate
"""
import math, sys
import numpy as np
import anatomy as A
import gait as G

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


N = 64
THETAS = (0.0, 18.0, 34.0, 50.0, 70.0, 90.0)

# 1. lengths, reach, ground (the walks at every turn, and every frame of every idle)
worst_len = 0.0
stretch = 0
minz = 1e9
_poses = [G.pose(k / N, th) for th in THETAS for k in range(N)] + [G.strip_pose(nm, k) for nm, n in G.COUNTS.items() if nm.startswith('idle') for k in range(n)]
for P in _poses:
    if True:
        for (s, i), J in P["legs"].items():
            L = A.LEG[i]
            for a, b, n in (("H", "K1", "fem"), ("K1", "K2", "pat"), ("K2", "A", "tib"), ("A", "M", "met"), ("M", "F", "tar")):
                d = np.linalg.norm(J[b] - J[a])
                worst_len = max(worst_len, abs(d - L[n]))
            if J["stretch"]:
                stretch += 1
            minz = min(minz, J["F"][2], J["M"][2] - 0.2)
check(worst_len < 1e-6, f"segment lengths drift by {worst_len:.4f}")
check(stretch == 0, f"{stretch} leg poses had to stretch")
check(minz > 0.0, f"a foot or tarsus is below the ground ({minz:.2f})")
print(f"lengths: worst error {worst_len:.2e}; stretched poses: {stretch}; lowest foot z {minz:.2f}")

# 2. skating: a planted foot is fixed in the world
worst_skate = 0.0
worst_pen = 0.0
for th in THETAS:
    v = A.STRIDE * math.cos(math.radians(th)); w = A.TURN * math.sin(math.radians(th))
    for side in (-1, 1):
        for i in (1, 2, 3, 4):
            prev = None; prev_planted = False
            steps = 600
            for n in range(steps):
                t = 0.25 + 3.0 * n / steps                      # unwrapped time, in cycles
                F, planted, q, lift = G.foot_track(side, i, t % 1.0, th)
                world = G._to_world(F - G.PIV, t, v, w)
                if prev is not None and planted and prev_planted:
                    worst_skate = max(worst_skate, float(np.linalg.norm(world[:2] - prev[:2])))
                prev, prev_planted = world, planted
check(worst_skate < 0.35, f"planted feet skate {worst_skate:.3f} BU between samples")
print(f"skating: worst world displacement of a planted foot between samples (3 cycles/600 samples): {worst_skate:.4f} BU")

# stance really is stationary: compare a planted foot at two moments of one stance
for th in (0.0, 50.0, 90.0):
    v = A.STRIDE * math.cos(math.radians(th)); w = A.TURN * math.sin(math.radians(th))
    side, i = 1, 1
    pts = []
    for t in np.linspace(0.0, 0.42, 20):                    # leg (1, 1) is in tetrapod A: planted through roughly 0..0.5
        F, planted, q, lift = G.foot_track(side, i, t % 1.0, th)
        if planted:
            pts.append(G._to_world(F - G.PIV, t, v, w))
    pts = np.array(pts)
    spread = float(np.ptp(pts[:, :2], axis=0).max()) if len(pts) else 99
    check(spread < 1e-6, f"planted foot moves {spread:.4f} in the world at theta {th}")
    print(f"theta {th:>4}: a stance of {len(pts)} samples keeps the foot within {spread:.1e} BU in the world")

# 3. all eight feet down at 0 and 0.5
for ph in (0.0, 0.5):
    for th in THETAS:
        n_down = sum(1 for side in (-1, 1) for i in (1, 2, 3, 4) if G.foot_track(side, i, ph, th)[1])
        check(n_down == 8, f"only {n_down} feet down at phase {ph} (theta {th})")
# and the tetrapods alternate: never more than 4 up, never fewer than 3 down in a row of the cycle
ups = []
for k in range(200):
    ph = k / 200
    ups.append(sum(1 for side in (-1, 1) for i in (1, 2, 3, 4) if not G.foot_track(side, i, ph, 0.0)[1]))
check(max(ups) <= 4, f"{max(ups)} feet up at once")
print("feet up at once: min", min(ups), "max", max(ups))

# 4. mirror: pose(phase + .5) is pose(phase) with X flipped (straight walk)
worst_m = 0.0
for k in range(N):
    P0, P1 = G.pose(k / N, 0.0), G.pose((k / N + 0.5) % 1.0, 0.0)
    for (s, i), J in P0["legs"].items():
        J2 = P1["legs"][(-s, i)]
        for key in ("H", "K1", "K2", "A", "M", "F"):
            m = J[key] * np.array([-1, 1, 1.0])
            worst_m = max(worst_m, float(np.linalg.norm(m - J2[key])))
check(worst_m < 1e-6, f"mirror error {worst_m:.4f}")
print(f"mirror symmetry error {worst_m:.2e}")

# 5. numbers worth knowing
P = G.pose(0.0, 0.0)
kz = [J["K1"][2] for J in P["legs"].values()]
print("knee height at phase 0: min %.0f max %.0f  (body length %.0f)" % (min(kz), max(kz), A.BODY_BU))
fx = [abs(J["F"][0]) for J in P["legs"].values()]
fy = [J["F"][1] for J in P["legs"].values()]
print("footprint: lateral up to %.0f, front %.0f, rear %.0f; pivot y %.1f" % (max(fx), max(fy), min(fy), G.PIV_Y))
print("step per cycle %.0f BU = %.2f body lengths; beta %.2f" % (A.STRIDE, A.STRIDE / A.BODY_BU, A.BETA))

if fails:
    print("\nFAILED:")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("\nall gait tests pass")
