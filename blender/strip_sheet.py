"""Contact sheet of one rendered strip on a light page:  python strip_sheet.py DIR STRIP OUT.png [px] [cols]"""
import sys, glob
from PIL import Image
d, name, out = sys.argv[1], sys.argv[2], sys.argv[3]
px = int(sys.argv[4]) if len(sys.argv) > 4 else 200
cols = int(sys.argv[5]) if len(sys.argv) > 5 else 8
files = sorted(glob.glob(f"{d}/{name}_*.png"))
rows = (len(files) + cols - 1) // cols
S = Image.new("RGB", (cols * px, rows * px), (240, 237, 230))
for k, f in enumerate(files):
    im = Image.open(f).convert("RGBA").crop((40, 30, 728, 718)).resize((px, px), Image.LANCZOS)
    t = Image.new("RGBA", im.size, (240, 237, 230, 255)); t.alpha_composite(im)
    S.paste(t.convert("RGB"), ((k % cols) * px, (k // cols) * px))
S.save(out)
print(len(files), "frames")
