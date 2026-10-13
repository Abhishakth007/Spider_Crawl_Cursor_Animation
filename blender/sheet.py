"""Contact sheet of frames on a light and a dark page:  python sheet.py out.png px frame1.png frame2.png ...  (px = size each frame is shown at)"""
import sys
from PIL import Image
out, px = sys.argv[1], int(sys.argv[2])
files = sys.argv[3:]
cols = min(len(files), 6)
rows = (len(files) + cols - 1) // cols
S = Image.new("RGB", (cols * px, rows * px * 2), (0, 0, 0))
for k, f in enumerate(files):
    im = Image.open(f).convert("RGBA").resize((px, px), Image.LANCZOS)
    for j, bg in enumerate(((240, 237, 230), (24, 26, 32))):
        t = Image.new("RGBA", (px, px), bg + (255,))
        t.alpha_composite(im)
        S.paste(t.convert("RGB"), ((k % cols) * px, ((k // cols) * 2 + j) * px))
S.save(out)
