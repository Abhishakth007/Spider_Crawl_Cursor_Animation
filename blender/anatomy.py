"""Dimensions of the spider, in Blender units (BU). Pure Python: the gait maths and the modeller both read this.

The spider faces +Y, stands on Z = 0, and is symmetric about X = 0 (side = +1 is +X). The carapace is centred on the origin;
the abdomen trails behind it. A leg is five rigid pieces between six joints:

    hip H -- femur -- knee K1 -- patella -- K2 -- tibia -- ankle A -- metatarsus -- M -- tarsus -- foot F

The proportions come from the reference walk cycle (tracked frame by frame): legs about 1.8 body lengths, the knees carried well
above a low body, the metatarsus and tarsus dropping steeply to the ground, and a stance as wide as the legs are long.
"""
import math

K = 0.90                  # legs and gait are scaled together by this (the reference spider is leggier than the hero references)
BODY_BU = 140.0          # chelicerae to spinnerets; the page's `size` is this length
HEAD_Y = 40.0            # front of the face, from the carapace centre
CT_Z = 38.0              # carapace centre height, standing (the reference carries its body high; the abdomen hangs low behind)
HIP_Z = 36.0             # hip height above the ground, standing
FOOT_R = 0.9             # radius of a foot (it rests this far above the ground)

# hips, as (|x|, y) from the carapace centre (z is HIP_Z). Legs 1 and 4 are the long ones, as in the reference.
HIPS = {1: (14.0, 18.0), 2: (19.0, 6.5), 3: (19.0, -6.0), 4: (14.0, -17.5)}

# lengths of the five rigid pieces (femur includes the trochanter)
_LEG = {
    1: dict(fem=76.0, pat=13.0, tib=66.0, met=64.0, tar=30.0),
    2: dict(fem=71.0, pat=12.0, tib=62.0, met=60.0, tar=28.0),
    3: dict(fem=62.0, pat=11.0, tib=52.0, met=52.0, tar=25.0),
    4: dict(fem=74.0, pat=12.0, tib=64.0, met=64.0, tar=29.0),
}
LEG = {i: {k: v * K for k, v in d.items()} for i, d in _LEG.items()}
BEND_PT = math.radians(22.0)     # patella-tibia joint: the tibia turns this much below the patella's line (knees are convex)
BEND_MT = math.radians(15.0)     # metatarsus-tarsus: the tarsus droops


def chord(a, b, bend):
    return math.sqrt(a * a + b * b + 2 * a * b * math.cos(bend))


def chords(i):
    L = LEG[i]
    return L["fem"], chord(L["pat"], L["tib"], BEND_PT), chord(L["met"], L["tar"], BEND_MT)


# where a foot is happiest, from its hip: angle from straight ahead (outwards) and distance along the ground. The reference's
# tracks put the centre of each foot's travel at these numbers (converted from its top view).
FOOT_ANGLE = {1: 19.0, 2: 73.0, 3: 108.0, 4: 142.0}
FOOT_REACH = {1: 148.0 * K, 2: 128.0 * K, 3: 108.0 * K, 4: 126.0 * K}
META_ELEV = {1: 58.0, 2: 62.0, 3: 64.0, 4: 60.0}        # slope of the distal link (ankle -> foot), degrees above the ground
KNEE_ELEV = {1: 84.0, 2: 84.0, 3: 84.0, 4: 84.0}         # how steeply the femur rises (degrees above horizontal); the knee swings out of
                                                         # the leg's own plane to get there, which is the spider's bowed "elbow"
KNEE_TILT = {1: 14.0, 2: 10.0, 3: 10.0, 4: 14.0}                 # a small fixed bow out of the leg's plane (degrees), so neighbours do not run parallel
KNEE_SIDE = {1: 1, 2: 1, 3: 1, 4: 1}                     # which way each knee bows out of its leg's plane: +1 backward-outward, -1 forward

# gait ---------------------------------------------------------------------------------------------------------------
STRIDE = 150.0 * K           # body travel per cycle, walking straight (BU). The reference's feet travel 0.55 body lengths per step.
DELTA = 0.03             # each tetrapod waits this much of a cycle before it lifts or lands again: all eight feet are down at
BETA = 0.5 + 2 * DELTA   # phase 0 and 0.5, which is where the page stops and starts it
TURN = math.radians(62.0)  # body rotation per cycle when it pivots on the spot
LIFT = {1: 40.0 * K, 2: 34.0 * K, 3: 31.0 * K, 4: 36.0 * K}
FLEX = math.radians(30.0)  # how much shallower the foot link gets at the top of a swing (the foot flicks forward as the leg lifts)   # how high a foot clears the ground in mid-swing
BULGE = {1: 9.0 * K, 2: 7.0 * K, 3: 6.0 * K, 4: 7.0 * K}      # how far outward the swing arcs (the reference's tracks)
# rear legs lift a hair before the front ones in each tetrapod (the reference's fits: legs 3 and 4 lead by 1-4 video frames)
LAG = {1: 0.012, 2: 0.020, 3: -0.008, 4: -0.012}
TETRA_A = {(1, 1), (-1, 2), (1, 3), (-1, 4)}   # (side, leg): L1 R2 L3 R4 against R1 L2 R3 L4, as the reference has them

# palps and face
PALP_BASE = (7.2, 30.5, -3.5)    # |x|, y, z from the carapace centre (carapace-local)
PALP_LEN = (11.0, 8.5, 8.5)

# eyes: (kind, |x|, y, radius, tilt). Jumping-spider layout: a big forward pair, two big on the corners, two tiny, two large
# on the sides of the raised back of the head.
EYES = [
    ("AME", 4.6, 31.4, 4.8),
    ("ALE", 11.6, 27.5, 3.2),
    ("PME", 9.2, 19.6, 1.35),
    ("PLE", 14.4, 14.6, 3.0),
]

# body ---------------------------------------------------------------------------------------------------------------
AB_ATTACH = (0.0, -22.0, -1.5)           # where the pedicel meets the carapace, from the carapace centre
AB_TILT = math.radians(13.0)             # the abdomen hangs down behind (positive pitches the rear down)
AB_LEN = 80.0
