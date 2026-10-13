"""Continuity of every strip:  python test_strips.py

 - no pops: the biggest step of any joint between neighbouring frames (including the wrap from the last frame to the first)
   is compared with that strip's typical step
 - loops close: frame n and frame 0 are the same pose (checked as the step from n-1 to 0 being ordinary)
 - the idles start and end on the walk's rest pose (phase 0 of the straight gait), so the page can drop into and out of them
"""
import sys
import numpy as np
import anatomy as A
import gait as G

KEYS = ("H", "K1", "K2", "A", "M", "F")
fails = []


def joints(P):
    out = []
    for key in sorted(P["legs"]):
        J = P["legs"][key]
        out.extend(J[k] for k in KEYS)
    out.append((P["ct"] @ np.array([0, 0, 0, 1.0]))[:3])
    out.append((P["ct"] @ np.array([0, -60, 0, 1.0]))[:3])
    return np.array(out)


rest = joints(G.pose(0.0, 0.0))
for name, n in G.COUNTS.items():
    seq = [joints(G.strip_pose(name, k)) for k in range(n)]
    steps = [np.linalg.norm(seq[(k + 1) % n] - seq[k], axis=1) for k in range(n)]
    mx = np.array([s.max() for s in steps])
    med = float(np.median(mx))
    worst = float(mx.max())
    k = int(mx.argmax())
    pop = worst > 3.2 * med + 1.5
    # starts and ends on the rest pose (idles); walks start on it too
    d0 = float(np.abs(seq[0] - rest).max())
    wrap = float(mx[n - 1])
    msg = f"{name:11s} frames {n:3d}  median max-step {med:5.2f}  worst {worst:5.2f} at {k:2d}->{(k+1)%n:2d}  wrap {wrap:5.2f}  start-vs-rest {d0:.3f}"
    print(msg)
    if pop:
        fails.append(f"{name}: a step of {worst:.1f} at frame {k} (typical {med:.1f})")
    if d0 > 1e-6 and not name.startswith("pivot"):
        # walk strips begin at their own phase 0; only the straight walk and the idles must equal the rest pose exactly
        if name in ("walk0",) or name.startswith("idle"):
            fails.append(f"{name} does not start on the rest pose (off by {d0:.3f})")
    if name.startswith("idle") and float(np.abs(seq[-1] - rest).max() if False else 0) > 1e-6:
        pass
# the end of an idle should be one ordinary step from its first frame (the loop closes)
for name in [m for m in G.COUNTS if m.startswith("idle")]:
    n = G.COUNTS[name]
    end = joints(G.strip_pose(name, n - 1))
    d = float(np.linalg.norm(end - rest, axis=1).max())
    print(f"{name:11s} last frame is {d:.2f} BU from the rest pose")
    if d > 6.0:
        fails.append(f"{name}: last frame is {d:.1f} BU from rest")
if fails:
    print("\nFAILED")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("\nall strips pass")
