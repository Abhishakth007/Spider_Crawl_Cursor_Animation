"""Materials for the spider, in two skins.

    spidey   red and blue with black seams: the Spider-Man spider of the references
    widow    gloss black with a red hourglass: the black widow of the first reference

A part's colour runs along its own length (object Y, 0 at the joint nearer the body, 1 at the far joint), so banded legs need no UVs.
"""
import os
import bpy
import bl_util as U
from bl_util import N, L, rgb, hexc

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "tex")

# ------------------------------------------------------------------------------------------------ the skins
_BLACK = rgb(10, 10, 13)
_NAVY = rgb(14, 22, 70)

SKINS = {
    "spidey": dict(
        name="spidey",
        legs={
            "fem": [(0.07, _BLACK), (0.80, rgb(150, 12, 22)), (1.0, _BLACK)],
            "pat": [(1.0, _BLACK)],
            "tib": [(0.10, _BLACK), (0.74, rgb(22, 44, 138)), (0.90, rgb(150, 12, 22)), (1.0, _BLACK)],
            "met": [(0.10, _BLACK), (0.52, rgb(150, 12, 22)), (0.90, rgb(18, 38, 116)), (1.0, _BLACK)],
            "tar": [(0.30, rgb(20, 28, 80)), (1.0, _BLACK)],
        },
        hair_tint=0.92,
        leg_rough=0.34, leg_coat=0.42,
        body_rough=0.30, body_coat=0.50,
        pattern="spidey",
        ring=rgb(178, 26, 20),
        beard=rgb(176, 150, 128),
        eye_glow=rgb(210, 40, 20),
        chel=rgb(16, 12, 16),
    ),
    "widow": dict(
        name="widow",
        legs={
            "fem": [(0.07, rgb(70, 16, 14)), (0.90, _BLACK), (1.0, rgb(60, 14, 12))],
            "pat": [(1.0, rgb(24, 8, 8))],
            "tib": [(0.10, rgb(60, 14, 12)), (0.92, _BLACK), (1.0, rgb(60, 14, 12))],
            "met": [(0.10, rgb(60, 14, 12)), (0.94, _BLACK), (1.0, rgb(50, 12, 10))],
            "tar": [(0.30, rgb(14, 8, 9)), (1.0, _BLACK)],
        },
        hair_tint=1.0,
        leg_rough=0.17, leg_coat=0.75,
        body_rough=0.14, body_coat=0.8,
        pattern="widow",
        ring=rgb(26, 12, 12),
        beard=rgb(70, 52, 46),
        eye_glow=rgb(150, 20, 14),
        chel=rgb(12, 6, 7),
    ),
}

AB_DIM = dict(x0=-36.0, x1=36.0, y0=-14.0, y1=-108.0)
CT_DIM = dict(x0=-26.0, x1=26.0, y0=36.0, y1=-30.0)
AB_SHIFT = -22.0                      # the abdomen's own origin sits at the pedicel, 22 behind the carapace centre


def _img(name, path, srgb=True):
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.load(path)
        img.name = name
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    return img


def _planar(nt, d, shift=0.0):
    """Object (x, y) -> texture (u, v) for a texture painted in plan view (row 0 = d.y0)."""
    tc = N(nt, "ShaderNodeTexCoord")
    mp = N(nt, "ShaderNodeMapping")
    mp.vector_type = "POINT"
    sx = 1.0 / (d["x1"] - d["x0"])
    sy = 1.0 / (d["y0"] - d["y1"])
    mp.inputs["Scale"].default_value = (sx, sy, 1.0)
    mp.inputs["Location"].default_value = (-d["x0"] * sx, (shift - d["y1"]) * sy, 0.0)
    L(nt, tc.outputs["Object"], mp.inputs["Vector"])
    return mp.outputs["Vector"], tc


def _tex(nt, img, vec, srgb=True):
    t = N(nt, "ShaderNodeTexImage")
    t.image = img
    t.interpolation = "Cubic"
    t.extension = "EXTEND"
    L(nt, vec, t.inputs["Vector"])
    return t


def _principled(nt, **inputs):
    out, bs = N(nt, "ShaderNodeOutputMaterial"), N(nt, "ShaderNodeBsdfPrincipled")
    L(nt, bs.outputs[0], out.inputs[0])
    for k, v in inputs.items():
        bs.inputs[k.replace("_", " ")].default_value = v
    return bs


def _micro_bump(nt, bs, tc, strength=0.12, scale=22.0, dist=0.35, normal_in=None, height_extra=None):
    nz = N(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = scale, 7.0
    L(nt, tc.outputs["Object"], nz.inputs[0])
    bp = N(nt, "ShaderNodeBump")
    bp.inputs["Strength"].default_value, bp.inputs["Distance"].default_value = strength, dist
    L(nt, nz.outputs["Fac"], bp.inputs["Height"])
    if normal_in is not None:
        L(nt, normal_in, bp.inputs["Normal"])
    return bp.outputs[0]


# ------------------------------------------------------------------------------------------------ chitin (legs, palps)
def _smooth(nt, v, a, b):
    mr = N(nt, "ShaderNodeMapRange")
    mr.clamp = True
    mr.interpolation_type = "SMOOTHSTEP"
    mr.inputs[1].default_value, mr.inputs[2].default_value = a, b
    mr.inputs[3].default_value, mr.inputs[4].default_value = 0.0, 1.0
    L(nt, v, mr.inputs[0])
    return mr.outputs[0]


def chitin(name, skin, seg, length, flat_color=None):
    """Glossy cuticle with its colour in soft bands along the segment, a mottled value, a fine pitted bump, matte joint membranes at
    both ends (no white button highlights) and a little occlusion."""
    sk = SKINS[skin]
    m, nt = U.new_mat(name)
    bs = _principled(nt)
    bs.inputs["Coat Roughness"].default_value = 0.10
    bs.inputs["Specular IOR Level"].default_value = 0.65
    t, tc = U.object_axis(nt, 1, length)
    if flat_color is not None:
        col = flat_color
    else:
        col = U.banded_color(nt, t, sk["legs"][seg], warp=0.02, noise_scale=3.0, tc=tc, soft=0.035)
    nz = N(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 2.2, 4.0
    L(nt, tc.outputs["Object"], nz.inputs[0])
    shade = U.math_node(nt, "MULTIPLY_ADD", nz.outputs["Fac"], 0.34, 0.80)
    ao = N(nt, "ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 7.0
    ao.samples = 4
    aoc = U.math_node(nt, "MULTIPLY_ADD", ao.outputs["AO"], 0.55, 0.45)
    shade2 = U.math_node(nt, "MULTIPLY", shade, aoc)
    mixc = N(nt, "ShaderNodeMix")
    mixc.data_type = "RGBA"
    mixc.blend_type = "MULTIPLY"
    mixc.inputs[0].default_value = 1.0
    L(nt, col, mixc.inputs[6])
    gray = N(nt, "ShaderNodeCombineColor")
    for k in range(3):
        L(nt, shade2, gray.inputs[k])
    L(nt, gray.outputs[0], mixc.inputs[7])
    L(nt, mixc.outputs[2], bs.inputs["Base Color"])
    # membranes: the first and last few percent of a piece are soft, dull tissue
    ends = U.math_node(nt, "MULTIPLY", _smooth(nt, t, 0.0, 0.07), _smooth(nt, U.math_node(nt, "SUBTRACT", 1.0, t), 0.0, 0.07))
    rn = U.math_node(nt, "MULTIPLY_ADD", nz.outputs["Fac"], 0.12, sk["leg_rough"] - 0.06)
    rmix = U.math_node(nt, "ADD", U.math_node(nt, "MULTIPLY", rn, ends), U.math_node(nt, "MULTIPLY", U.math_node(nt, "SUBTRACT", 1.0, ends), 0.7))
    L(nt, rmix, bs.inputs["Roughness"])
    L(nt, U.math_node(nt, "MULTIPLY", ends, sk["leg_coat"]), bs.inputs["Coat Weight"])
    L(nt, _micro_bump(nt, bs, tc, 0.14, 26.0, 0.3), bs.inputs["Normal"])
    return m


def plain(name, color, rough=0.3, coat=0.4, metallic=0.0, sss=0.0):
    m, nt = U.new_mat(name)
    bs = _principled(nt)
    bs.inputs["Base Color"].default_value = color
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Coat Weight"].default_value = coat
    bs.inputs["Coat Roughness"].default_value = 0.1
    bs.inputs["Metallic"].default_value = metallic
    if sss:
        bs.inputs["Subsurface Weight"].default_value = sss
        bs.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
        bs.inputs["Subsurface Scale"].default_value = 0.6
    return m


# ------------------------------------------------------------------------------------------------ the painted body parts
def body(name, skin, part):
    """part: 'abdomen' or 'carapace'. Colour and bump painted in plan view, mapped from object coordinates."""
    sk = SKINS[skin]
    d = AB_DIM if part == "abdomen" else CT_DIM
    m, nt = U.new_mat(name)
    bs = _principled(nt)
    bs.inputs["Roughness"].default_value = sk["body_rough"]
    bs.inputs["Coat Weight"].default_value = sk["body_coat"]
    bs.inputs["Coat Roughness"].default_value = 0.12
    bs.inputs["Specular IOR Level"].default_value = 0.7
    bs.inputs["Subsurface Weight"].default_value = 0.04
    bs.inputs["Subsurface Radius"].default_value = (1.0, 0.3, 0.15)
    bs.inputs["Subsurface Scale"].default_value = 0.8
    vec, tc = _planar(nt, d, AB_SHIFT if part == "abdomen" else 0.0)
    ct = _tex(nt, _img(f"{sk['pattern']}_{part}_c", os.path.join(TEX, f"{sk['pattern']}_{part}_color.png")), vec)
    L(nt, ct.outputs["Color"], bs.inputs["Base Color"])
    bt = _tex(nt, _img(f"{sk['pattern']}_{part}_b", os.path.join(TEX, f"{sk['pattern']}_{part}_bump.png"), srgb=False), vec)
    bp = N(nt, "ShaderNodeBump")
    bp.inputs["Strength"].default_value, bp.inputs["Distance"].default_value = 0.55, 0.5
    L(nt, bt.outputs["Color"], bp.inputs["Height"])
    n2 = _micro_bump(nt, bs, tc, 0.10, 30.0, 0.25, normal_in=bp.outputs[0])
    L(nt, n2, bs.inputs["Normal"])
    return m


# ------------------------------------------------------------------------------------------------ hair
def _hair_core(nt, color_out, rough=0.32, tint=1.0, radial=0.45, coat=0.12):
    out, hb = N(nt, "ShaderNodeOutputMaterial"), N(nt, "ShaderNodeBsdfHairPrincipled")
    hb.parametrization = "COLOR"
    L(nt, hb.outputs[0], out.inputs[0])
    hb.inputs["Roughness"].default_value = rough
    hb.inputs["Radial Roughness"].default_value = radial
    hb.inputs["Coat"].default_value = coat * 0.5
    hb.inputs["IOR"].default_value = 1.55
    for k, v in (("Random Color", 0.16), ("Random Roughness", 0.25)):
        if k in hb.inputs:
            hb.inputs[k].default_value = v
    if tint != 1.0:
        hsv = N(nt, "ShaderNodeHueSaturation")
        hsv.inputs["Value"].default_value = tint
        hsv.inputs["Saturation"].default_value = 1.0
        L(nt, color_out, hsv.inputs["Color"])
        color_out = hsv.outputs["Color"]
    L(nt, color_out, hb.inputs["Color"])
    return hb


def hair_banded(name, skin, seg, length, rough=0.32):
    sk = SKINS[skin]
    m, nt = U.new_mat(name)
    t, tc = U.object_axis(nt, 1, length)
    col = U.banded_color(nt, t, sk["legs"][seg], warp=0.018, noise_scale=3.0, tc=tc)
    _hair_core(nt, col, rough=rough, tint=sk["hair_tint"])
    return m


def hair_planar(name, skin, part, rough=0.34):
    sk = SKINS[skin]
    d = AB_DIM if part == "abdomen" else CT_DIM
    m, nt = U.new_mat(name)
    vec, tc = _planar(nt, d, AB_SHIFT if part == "abdomen" else 0.0)
    ct = _tex(nt, _img(f"{sk['pattern']}_{part}_c", os.path.join(TEX, f"{sk['pattern']}_{part}_color.png")), vec)
    _hair_core(nt, ct.outputs["Color"], rough=rough, tint=sk["hair_tint"])
    return m


def hair_flat(name, color, rough=0.34, coat=0.1):
    m, nt = U.new_mat(name)
    rgbn = N(nt, "ShaderNodeRGB")
    rgbn.outputs[0].default_value = color
    _hair_core(nt, rgbn.outputs[0], rough=rough, coat=coat)
    return m


# ------------------------------------------------------------------------------------------------ eyes, fangs
def eye(name, skin, big=False):
    sk = SKINS[skin]
    m, nt = U.new_mat(name)
    bs = _principled(nt)
    bs.inputs["Base Color"].default_value = (0.003, 0.003, 0.005, 1)
    bs.inputs["Roughness"].default_value = 0.035
    bs.inputs["Coat Weight"].default_value = 1.0
    bs.inputs["Coat Roughness"].default_value = 0.015
    bs.inputs["Specular IOR Level"].default_value = 1.0
    lw = N(nt, "ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    mr = N(nt, "ShaderNodeMapRange")
    mr.inputs[1].default_value, mr.inputs[2].default_value = 0.55, 0.05
    mr.inputs[3].default_value, mr.inputs[4].default_value = 0.0, 1.0
    L(nt, lw.outputs["Facing"], mr.inputs[0])
    em = U.math_node(nt, "MULTIPLY", mr.outputs[0], 0.18 if big else 0.06)
    bs.inputs["Emission Color"].default_value = sk["eye_glow"]
    L(nt, em, bs.inputs["Emission Strength"])
    return m


def fang(skin):
    m, nt = U.new_mat("fang")
    bs = _principled(nt)
    bs.inputs["Base Color"].default_value = rgb(52, 14, 6)
    bs.inputs["Roughness"].default_value = 0.2
    bs.inputs["Coat Weight"].default_value = 0.7
    bs.inputs["Subsurface Weight"].default_value = 0.35
    bs.inputs["Subsurface Radius"].default_value = (1.0, 0.4, 0.2)
    bs.inputs["Subsurface Scale"].default_value = 0.6
    return m
