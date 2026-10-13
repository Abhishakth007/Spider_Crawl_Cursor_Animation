"""Paint the body textures (system Python, PIL + numpy).  python patterns.py

Each texture is laid out in the plan view of the part it covers, in the part's own units, so the shader can map it straight from
object coordinates (x, y) without UVs:

    abdomen   x in [-36, 36], y in [-108, -14]      (y = 0 is the carapace centre; the abdomen trails behind)
    carapace  x in [-26, 26], y in [-30, 36]

Two skins: `spidey` (the red-and-blue one the page calls classic: red and blue with a black web and an emblem) and `widow` (gloss black, red hourglass).
Each gets a colour map (sRGB) and a bump map (greyscale; the seams and striae stand proud).
"""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tex")
os.makedirs(OUT, exist_ok=True)
SS = 2                                     # supersampling for the line work

AB = dict(x0=-36.0, x1=36.0, y0=-14.0, y1=-108.0, w=2048, h=2688)       # y0 is the front (v = 0)
CT = dict(x0=-26.0, x1=26.0, y0=36.0, y1=-30.0, w=2048, h=2600)

RED = (196, 22, 30)
RED_D = (126, 12, 20)
RED_HI = (222, 44, 38)
BLUE = (28, 62, 168)
BLUE_D = (14, 28, 96)
BLACK = (8, 8, 11)


class Plan:
    def __init__(self, d):
        self.d = d
        self.w, self.h = d["w"] * SS, d["h"] * SS
        self.sx = self.w / (d["x1"] - d["x0"])
        self.sy = self.h / (d["y1"] - d["y0"])        # negative direction of y: y0 -> top row

    def px(self, x, y):
        return ((x - self.d["x0"]) * self.sx, (y - self.d["y0"]) * self.sy)

    def length(self, bu):
        return bu * self.sx


def noise(h, w, scale, seed, octaves=4):
    r = np.random.RandomState(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        gh, gw = max(2, int(h / scale * (2 ** o)) + 2), max(2, int(w / scale * (2 ** o)) + 2)
        g = r.rand(gh, gw).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * (np.asarray(im, np.float32) / 255.0)
        tot += amp
        amp *= 0.5
    return out / tot


def to_img(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def finish(img, d, name, bump=None, blur=0.0):
    img = img.resize((d["w"], d["h"]), Image.LANCZOS)
    img.convert("RGB").save(os.path.join(OUT, name + "_color.png"))
    if bump is not None:
        b = bump.resize((d["w"], d["h"]), Image.LANCZOS)
        if blur:
            b = b.filter(ImageFilter.GaussianBlur(blur))
        b.convert("L").save(os.path.join(OUT, name + "_bump.png"))


def poly_curve(draw, pts, width, fill):
    """A thick polyline with round ends."""
    draw.line(pts, fill=fill, width=int(width), joint="curve")
    r = width / 2
    for (x, y) in (pts[0], pts[-1]):
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)


# ------------------------------------------------------------------------------------------------ the emblem
def emblem(P, draw_c, draw_b, cx, cy, size, rot=0.0):
    """The black spider: oval abdomen, small head, four pairs of bent legs. size = body length in BU."""
    fill_c, fill_b = BLACK, 255
    for draw, fill in ((draw_c, fill_c), (draw_b, fill_b)):
        # body
        def E(x, y, rx, ry):
            X0, Y0 = P.px(cx + x - rx, cy + y + ry)
            X1, Y1 = P.px(cx + x + rx, cy + y - ry)
            draw.ellipse((X0, Y1, X1, Y0) if False else (min(X0, X1), min(Y0, Y1), max(X0, X1), max(Y0, Y1)), fill=fill)
        E(0, -0.10 * size, 0.17 * size, 0.30 * size)            # abdomen (pointing back = -y)
        E(0, 0.26 * size, 0.10 * size, 0.12 * size)             # head
        E(0, 0.12 * size, 0.12 * size, 0.12 * size)             # thorax
        # legs: (start y on the body, knee (x, y), foot (x, y)), mirrored
        legs = [
            (0.22, (0.30, 0.50), (0.62, 0.34)),
            (0.14, (0.42, 0.28), (0.86, 0.20)),
            (0.08, (0.42, 0.02), (0.84, -0.18)),
            (0.02, (0.34, -0.22), (0.62, -0.58)),
        ]
        for (ys, k, f) in legs:
            for s in (-1, 1):
                pts = [P.px(cx + s * 0.06 * size, cy + ys * size), P.px(cx + s * k[0] * size, cy + k[1] * size), P.px(cx + s * f[0] * size, cy + f[1] * size)]
                poly_curve(draw, pts, P.length(0.065 * size), fill)


# ------------------------------------------------------------------------------------------------ spidey abdomen
def spidey_abdomen():
    d = AB
    P = Plan(d)
    W, H = P.w, P.h
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    x = d["x0"] + xx / P.sx
    y = d["y0"] + yy / P.sy
    n1 = noise(H, W, 900, 3, 3)
    n2 = noise(H, W, 260, 5, 4)
    # blue flanks and tail, red back; the boundary wanders a little and is cut by the web below
    edge = 16.5 + 4.2 * np.sin(y / 9.0 + 1.0) + 7.0 * (n1 - 0.5)
    tail = np.clip((-(y + 84.0)) / 5.0, 0, 1)
    blue_w = np.clip((np.abs(x) - edge) / 2.2, 0, 1)
    blue_w = np.maximum(blue_w, tail)
    base = np.zeros((H, W, 3), np.float32)
    red = np.array(RED, np.float32)[None, None, :] * (0.88 + 0.24 * n2[..., None]) + np.array((10, 0, 0), np.float32)
    redhi = np.array(RED_HI, np.float32)[None, None, :]
    red = red * (1 - 0.35 * np.clip(1.0 - np.abs(x) / 15.0, 0, 1)[..., None] * (n1[..., None] > 0.5)) + redhi * 0.0
    blue = np.array(BLUE, np.float32)[None, None, :] * (0.82 + 0.3 * n2[..., None])
    deep = np.clip((np.abs(x) - 26.0) / 8.0, 0, 1)[..., None]
    blue = blue * (1 - deep) + np.array(BLUE_D, np.float32)[None, None, :] * deep
    base = red * (1 - blue_w[..., None]) + blue * blue_w[..., None]
    img_c = to_img(base)
    img_b = Image.new("L", (W, H), 0)
    dc, db = ImageDraw.Draw(img_c), ImageDraw.Draw(img_b)
    # the web: radial threads from the emblem, scalloped arcs between them
    cx, cy = 0.0, -52.0
    nrad = 18
    radial_w = P.length(0.85)
    rmax = 70.0
    angs = [2 * math.pi * k / nrad + math.pi / nrad for k in range(nrad)]
    for a in angs:
        pts = [P.px(cx + 7.0 * math.cos(a), cy + 8.0 * math.sin(a)), P.px(cx + rmax * math.cos(a), cy + rmax * 1.0 * math.sin(a))]
        for draw, fill in ((dc, BLACK), (db, 255)):
            poly_curve(draw, pts, radial_w, fill)
    for r in (13.0, 21.0, 30.0, 40.0, 52.0):
        for k in range(nrad):
            a0, a1 = angs[k], angs[(k + 1) % nrad] + (2 * math.pi if k == nrad - 1 else 0)
            pts = []
            for s in np.linspace(0, 1, 16):
                a = a0 + (a1 - a0) * s
                sag = 1.0 - 0.13 * math.sin(math.pi * s)          # the thread sags toward the centre between the spokes
                pts.append(P.px(cx + r * sag * math.cos(a), cy + r * 1.0 * sag * math.sin(a)))
            for draw, fill in ((dc, BLACK), (db, 255)):
                poly_curve(draw, pts, P.length(0.62), fill)
    emblem(P, dc, db, cx, cy, 30.0)
    # a dark ring where the abdomen meets the pedicel
    for draw, fill in ((dc, BLACK), (db, 255)):
        X0, Y0 = P.px(-9, -12); X1, Y1 = P.px(9, -26)
    finish(img_c, d, "spidey_abdomen", img_b, blur=1.1)


# ------------------------------------------------------------------------------------------------ spidey carapace
def spidey_carapace():
    d = CT
    P = Plan(d)
    W, H = P.w, P.h
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    x = d["x0"] + xx / P.sx
    y = d["y0"] + yy / P.sy
    n1 = noise(H, W, 500, 11, 3)
    n2 = noise(H, W, 120, 12, 4)
    # red, a little more orange toward the face, darker in the rear groove
    t = np.clip((y + 30.0) / 66.0, 0, 1)
    base = np.zeros((H, W, 3), np.float32)
    col0 = np.array(RED_D, np.float32); col1 = np.array(RED, np.float32); col2 = np.array((214, 58, 28), np.float32)
    c = col0[None, None, :] * (1 - np.clip(t * 2.2, 0, 1))[..., None] + col1[None, None, :] * np.clip(t * 2.2, 0, 1)[..., None]
    c = c * (1 - np.clip((t - 0.55) * 2.2, 0, 1))[..., None] + col2[None, None, :] * np.clip((t - 0.55) * 2.2, 0, 1)[..., None]
    c = c * (0.86 + 0.28 * n2[..., None])
    # a dark mask over the face behind the eyes' ring, ragged edge
    face = np.clip((y - (14.0 + 3.0 * (n1 - 0.5) * 2)) / 3.0, 0, 1) * np.clip(1.15 - (np.abs(x) / 22.0) ** 3, 0, 1)
    c = c * (1 - 0.82 * face[..., None]) + np.array(BLACK, np.float32)[None, None, :] * 0.82 * face[..., None]
    img_c = to_img(c)
    img_b = Image.new("L", (W, H), 0)
    dc, db = ImageDraw.Draw(img_c), ImageDraw.Draw(img_b)
    rnd = random.Random(7)
    # radial striae from the thoracic groove
    fx, fy = 0.0, -6.0
    for k in range(120):
        a = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(3.0, 8.0)
        r1 = r0 + rnd.uniform(5.0, 17.0)
        pts = [P.px(fx + r0 * math.cos(a) * 0.9, fy + r0 * math.sin(a) * 1.15), P.px(fx + r1 * math.cos(a) * 0.9, fy + r1 * math.sin(a) * 1.15)]
        w = rnd.uniform(0.25, 0.7)
        poly_curve(dc, pts, P.length(w), (40, 6, 10))
        poly_curve(db, pts, P.length(w), 210)
    # the thoracic fovea and the cervical groove
    for draw, fill in ((dc, BLACK), (db, 255)):
        X0, Y0 = P.px(-1.1, -2.0); X1, Y1 = P.px(1.1, -11.0)
        draw.ellipse((X0, Y0, X1, Y1), fill=fill)
        pts = [P.px(-9.5, 8.5), P.px(-4.0, 6.0), P.px(0, 5.2), P.px(4.0, 6.0), P.px(9.5, 8.5)]
        poly_curve(draw, pts, P.length(0.7), fill)
    finish(img_c, d, "spidey_carapace", img_b, blur=1.4)


# ------------------------------------------------------------------------------------------------ widow
def widow_abdomen():
    d = AB
    P = Plan(d)
    W, H = P.w, P.h
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    x = d["x0"] + xx / P.sx
    y = d["y0"] + yy / P.sy
    n1 = noise(H, W, 600, 21, 3)
    n2 = noise(H, W, 140, 22, 4)
    base = np.zeros((H, W, 3), np.float32) + np.array((7, 7, 9), np.float32)
    base = base * (0.8 + 0.7 * n2[..., None]) + np.array((10, 2, 3), np.float32) * np.clip(n1 - 0.55, 0, 1)[..., None] * 3
    img_c = to_img(base)
    img_b = Image.new("L", (W, H), 0)
    dc, db = ImageDraw.Draw(img_c), ImageDraw.Draw(img_b)
    # the hourglass, bright and slightly glowing red, on the back (as in the reference)
    hg = [(-10.5, -34.0), (10.5, -34.0), (3.0, -53.0), (11.0, -72.0), (-11.0, -72.0), (-3.0, -53.0)]
    pts = [P.px(*p) for p in hg]
    dc.polygon(pts, fill=(205, 16, 22))
    # inner glow: a lighter core
    core = [(-6.0, -38.0), (6.0, -38.0), (1.6, -53.0), (6.0, -68.0), (-6.0, -68.0), (-1.6, -53.0)]
    dc.polygon([P.px(*p) for p in core], fill=(236, 44, 36))
    img_c = img_c.filter(ImageFilter.GaussianBlur(P.length(0.35)))
    finish(img_c, d, "widow_abdomen", img_b, blur=1.0)


def widow_carapace():
    d = CT
    P = Plan(d)
    W, H = P.w, P.h
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    n2 = noise(H, W, 130, 31, 4)
    base = np.zeros((H, W, 3), np.float32) + np.array((9, 8, 10), np.float32)
    base = base * (0.8 + 0.7 * n2[..., None])
    img_c = to_img(base)
    img_b = Image.new("L", (W, H), 0)
    dc, db = ImageDraw.Draw(img_c), ImageDraw.Draw(img_b)
    rnd = random.Random(8)
    fx, fy = 0.0, -6.0
    for k in range(90):
        a = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(3.0, 8.0); r1 = r0 + rnd.uniform(5.0, 16.0)
        pts = [P.px(fx + r0 * math.cos(a) * 0.9, fy + r0 * math.sin(a) * 1.15), P.px(fx + r1 * math.cos(a) * 0.9, fy + r1 * math.sin(a) * 1.15)]
        poly_curve(db, pts, P.length(rnd.uniform(0.25, 0.6)), 180)
    X0, Y0 = P.px(-1.1, -2.0); X1, Y1 = P.px(1.1, -11.0)
    db.ellipse((X0, Y0, X1, Y1), fill=255)
    finish(img_c, d, "widow_carapace", img_b, blur=1.4)


if __name__ == "__main__":
    for fn in (spidey_abdomen, spidey_carapace, widow_abdomen, widow_carapace):
        fn()
        print("painted", fn.__name__)
