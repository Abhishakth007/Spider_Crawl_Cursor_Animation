"""Render setup shared by the look-dev stills and the sprite renders: Cycles on the GPU (OptiX), soft symmetric studio light, an
orthographic camera that looks down at the spider (leaning a little in from the front, so the face and the knees show), and a
shadow catcher so the sprite carries its own soft shadow: dark where a foot is planted, wider and fainter under a lifted one.

The lights are symmetric about the spider's own axis, so a sprite mirrored in the page still lights correctly.
"""
import math, time
import bpy
from mathutils import Vector, Matrix


def use_gpu():
    pref = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            pref.compute_device_type = kind
            pref.refresh_devices()
            ok = False
            for d in pref.devices:
                d.use = d.type == kind
                ok = ok or d.type == kind
            if ok:
                bpy.context.scene.cycles.device = "GPU"
                return kind
        except Exception as e:  # noqa
            print("gpu", kind, e)
    bpy.context.scene.cycles.device = "CPU"
    return "CPU"


def sun(name, elev_deg, az_deg, energy, ang, color=(1, 1, 1), collection=None):
    d = bpy.data.lights.new(name, "SUN")
    d.energy, d.angle, d.color = energy, math.radians(ang), color
    o = bpy.data.objects.new(name, d)
    (collection or bpy.context.scene.collection).objects.link(o)
    e, a = math.radians(elev_deg), math.radians(az_deg)
    # a sun shines down its -Z; aim it so the light arrives from azimuth az (0 = from the front, +Y) at elevation e
    o.rotation_euler = (math.radians(90) - e, 0, math.radians(180) + a)
    return o


def setup(res=768, samples=128, elev=76.0, ortho=480.0, target=(0.0, 12.0, 0.0), exposure=0.0, transparent=True, shadow=True,
          denoiser="OPTIX", key=3.2, fill=1.8, sky=0.30, tonemap="Standard", shadow_strength=1.6):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    kind = use_gpu()
    cy = sc.cycles
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.012
    cy.use_denoising = True
    cy.denoiser = denoiser
    try:
        cy.denoising_use_gpu = True
    except Exception:
        pass
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces, cy.transmission_bounces = 6, 3, 4, 4
    cy.sample_clamp_indirect = 8.0
    cy.caustics_reflective = cy.caustics_refractive = False
    try:
        sc.cycles_curves.shape = "THICK"
        sc.cycles_curves.subdivisions = 2
    except Exception as e:
        print("curves", e)
    sc.render.film_transparent = transparent
    sc.render.filter_size = 1.1
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.use_persistent_data = True
    sc.view_settings.view_transform = tonemap
    sc.view_settings.look = "None"
    sc.view_settings.exposure = exposure

    w = bpy.data.worlds.new("sky")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.96, 0.93, 0.90, 1)
    bg.inputs["Strength"].default_value = sky

    spider_lights = bpy.data.collections.new("spider_lights")
    sc.collection.children.link(spider_lights)
    lights = [
        sun("key", 62, 0, key, 16, (1.0, 0.97, 0.92)),
        sun("softbox", 88, 0, 1.4, 34, (1.0, 0.98, 0.96)),            # a big soft overhead: wide highlights on the gloss
        sun("rimL", 24, 145, fill, 9, (1.0, 0.90, 0.78)),
        sun("rimR", 24, -145, fill, 9, (1.0, 0.90, 0.78)),
        sun("bounce", 10, 0, 0.45, 40, (1.0, 0.88, 0.72)),
        sun("side", 30, 90, 0.55, 30, (0.92, 0.95, 1.0)),
        sun("side2", 30, -90, 0.55, 30, (0.92, 0.95, 1.0)),
    ]
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho
    cam.data.clip_start, cam.data.clip_end = 1, 4000
    aim(cam, elev, target)
    sc.camera = cam
    floor = None
    if shadow:
        me = bpy.data.meshes.new("floor")
        me.from_pydata([(-3000, -3000, 0), (3000, -3000, 0), (3000, 3000, 0), (-3000, 3000, 0)], [], [(0, 1, 2, 3)])
        floor = bpy.data.objects.new("floor", me)
        sc.collection.objects.link(floor)
        floor.is_shadow_catcher = True
        # the shadow comes from its own lights, which light only the floor: a soft overhead sun (the planted foot's dark contact spot,
        # the body's pool of shade) and a broad fill (how far the shade spreads under a lifted foot). Symmetric, so mirrored sprites match.
        floor_coll = bpy.data.collections.new("floor_only")
        sc.collection.children.link(floor_coll)
        floor_coll.objects.link(floor)
        sc.collection.objects.unlink(floor)
        for l in (sun("shadow_sun", 84, 0, shadow_strength, 11, (1, 1, 1)), sun("shadow_fill", 62, 180, shadow_strength * 0.6, 55, (1, 1, 1))):
            l.light_linking.receiver_collection = floor_coll
            lights.append(l)
    return kind, cam, floor, lights


def aim(cam, elev, target, front=True):
    """Orthographic camera above the spider, leaning in `elev` degrees from the ground. front=True puts it in front of the spider
    (so the face and the eyes show) and rolls it so that +Y, the way the spider faces, is the top of the image."""
    e = math.radians(elev)
    c, s = math.cos(e), math.sin(e)
    t = Vector(target)
    if front:
        cam.location = t + Vector((0, 900 * c, 900 * s))
        X, Y, Z = Vector((1, 0, 0)), Vector((0, s, -c)), Vector((0, c, s))
    else:
        cam.location = t + Vector((0, -900 * c, 900 * s))
        X, Y, Z = Vector((1, 0, 0)), Vector((0, s, c)), Vector((0, -c, s))
    cam.rotation_euler = Matrix((X, Y, Z)).transposed().to_euler()


def aim_view(cam, elev, az, target, ortho):
    """A free camera at azimuth az (0 = behind the spider, 180 = in front of it) and elevation elev."""
    cam.data.ortho_scale = ortho
    ee, a = math.radians(elev), math.radians(az)
    t = Vector(target)
    off = Vector((900 * math.cos(ee) * math.sin(a), -900 * math.cos(ee) * math.cos(a), 900 * math.sin(ee)))
    cam.location = t + off
    d = (t - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def render(path):
    sc = bpy.context.scene
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - t


def link_lights_to_spider(floor):
    """Key, rim and fill light only the spider; the floor is lit by its own lights (see setup)."""
    sc = bpy.context.scene
    coll = bpy.data.collections.new("spider_only")
    sc.collection.children.link(coll)
    for ob in list(bpy.data.objects):
        if ob.type in {"LIGHT", "CAMERA"} or ob is floor:
            continue
        if ob.name not in coll.objects:
            coll.objects.link(ob)
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and not ob.name.startswith("shadow"):
            ob.light_linking.receiver_collection = coll
