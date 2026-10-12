"""Contact sheet of the walk cycle: N frames of a gait, small, top view.
    blender -b --factory-startup -P gait_sheet.py -- OUT.png [--theta 0] [--frames 16] [--res 220] [--samples 24] [--cols 8]
"""
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bpy
import spider_model as M, spider_motion as MO, spider_render as R
argv = sys.argv[sys.argv.index("--") + 1:]
opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
out = os.path.abspath(argv[0]); theta = float(opt("--theta", "0")); n = int(opt("--frames", "16")); res = int(opt("--res", "220"))
samples = int(opt("--samples", "24")); cols = int(opt("--cols", "8")); elev = float(opt("--elev", "78"))
tmp = os.path.join(os.path.dirname(out), "_g"); os.makedirs(tmp, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sp = M.build()
R.setup(res=res, samples=samples, elev=elev, ortho=330)
for k in range(n):
    MO.apply_pose(sp, MO.gait_pose(k / n, theta))
    bpy.context.view_layer.update()
    R.render(os.path.join(tmp, f"f{k:02d}.png"))
print("FRAMES", tmp)
