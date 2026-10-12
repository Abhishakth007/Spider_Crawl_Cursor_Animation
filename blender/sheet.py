"""python sheet.py "GLOB" OUT.png [cols] [crop]   — lay rendered frames out on the page colour (crop = pixels trimmed per side)."""
import sys, glob
from PIL import Image
pat, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 8
crop = int(sys.argv[4]) if len(sys.argv) > 4 else 0
fs = sorted(glob.glob(pat))
ims = []
for f in fs:
    im = Image.open(f).convert("RGBA")
    if crop:
        im = im.crop((crop, crop, im.width - crop, im.height - crop))
    ims.append(im)
w, h = ims[0].size
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGBA", (cols * w, rows * h), (244, 241, 234, 255))
for k, im in enumerate(ims):
    sheet.alpha_composite(im, ((k % cols) * w, (k // cols) * h))
sheet.convert("RGB").save(out)
print(out, sheet.size, len(ims))
