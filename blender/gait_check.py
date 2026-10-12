import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bpy
import spider_model as M, spider_motion as MO
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
# only need lengths
class SP: pass
sp = SP(); sp.leg_len = {i: tuple(v * M.LEG_SCALE[i] for v in (M.B1, M.B2, M.B3)) for i in (1,2,3,4)}
worst = 0; rmax = 0; zmin = 9
for theta in (0, 30, 60, 90):
    for k in range(64):
        ph = k / 64
        pose = MO.gait_pose(ph, theta)
        loc, pitch, roll, yaw = pose["ct"]
        ctm = __import__("mathutils").Matrix.Translation(Vector((0,0,M.CT_Z)) + loc) @ MO.rot(pitch, roll, yaw)
        for side in (-1, 1):
            for i in (1,2,3,4):
                hx, hy = M.HIPS[i]
                H = ctm @ Vector((side*hx, hy, M.HIP_Z - M.CT_Z))
                F = pose["feet"][(side,i)]
                knee, ankle = MO.solve_leg(H, F, sp.leg_len[i], MO.META_ELEV[i], MO.POLE_TILT[i])
                c = sp.leg_len[i][2]
                tip = ankle + (F-ankle).normalized()*c
                err = (tip - F).length
                worst = max(worst, err)
                rmax = max(rmax, math.hypot(F.x, F.y + 2))
print("worst foot error", round(worst, 3), "max foot radius from (0,-2):", round(rmax, 1))
