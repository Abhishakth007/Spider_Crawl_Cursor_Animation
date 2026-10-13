"""Judge a render at the size it will really be seen:  python smallview.py in.png out.png [--px 192] [--zoom 3]

Shrinks the way pack.py does (premultiplied Lanczos + the same unsharp), then shows it on a light and a dark page, at 1x and enlarged.
"""
import sys
from PIL import Image, ImageFilter

a = sys.argv
px = int(a[a.index("--px") + 1]) if "--px" in a else 192
zoom = int(a[a.index("--zoom") + 1]) if "--zoom" in a else 3
im = Image.open(a[1]).convert("RGBA")
pm = im.convert("RGBa")
while pm.width > px * 2:
    pm = pm.resize((pm.width // 2, pm.height // 2), Image.LANCZOS)
pm = pm.resize((px, px), Image.LANCZOS)
sm = pm.convert("RGBA")
rgb = sm.convert("RGB").filter(ImageFilter.UnsharpMask(radius=0.9, percent=70, threshold=2))
al = sm.getchannel("A")
sm = rgb.convert("RGBA")
sm.putalpha(al)
tiles = []
for bg in ((244, 241, 234), (22, 24, 30)):
    base = Image.new("RGBA", (px, px), bg + (255,))
    base.alpha_composite(sm)
    tiles.append(base.convert("RGB"))
W = px * zoom
out = Image.new("RGB", (W * 2 + px + 30, W), (128, 128, 128))
x = 0
for t in tiles:
    out.paste(t.resize((W, W), Image.NEAREST), (x, 0))
    x += W
out.paste(tiles[0], (x + 10, 10))
out.paste(tiles[1], (x + 10, 20 + px))
out.save(a[2])
