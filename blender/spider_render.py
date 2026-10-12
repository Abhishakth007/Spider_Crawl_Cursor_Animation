"""Render setup shared by the look-dev stills and the sprite renders: OptiX on the GPU, three suns and a dim sky, an
orthographic camera that looks down at the spider (tilted a little, so the face and the knees show)."""
import math, time
import bpy
from mathutils import Vector


def use_gpu(cpu_too=False):
    pref = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            pref.compute_device_type = kind
            pref.refresh_devices() if hasattr(pref, "refresh_devices") else None
            devs = pref.get_devices_for_type(kind) if hasattr(pref, "get_devices_for_type") else pref.devices
            ok = False
            for d in pref.devices:
                d.use = (d.type == kind) or (cpu_too and d.type == "CPU")
                ok = ok or (d.type == kind)
            if ok:
                bpy.context.scene.cycles.device = "GPU"
                return kind
        except Exception as e:  # noqa
            print("gpu", kind, e)
    bpy.context.scene.cycles.device = "CPU"
    return "CPU"


def setup(res=512, samples=96, elev=78.0, ortho=330.0, target=(0.0, 0.0, 14.0), key=3.4, fill=1.9, sky=0.28, exposure=0.0,
          denoiser="OPENIMAGEDENOISE", transparent=True, floor=False):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    kind = use_gpu()
    cy = sc.cycles
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.01
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
        bpy.context.scene.cycles_curves.shape = "THICK"
        bpy.context.scene.cycles_curves.subdivisions = 2
    except Exception as e:
        print("curves", e)
    sc.render.film_transparent = transparent
    sc.render.filter_size = 1.1
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.use_persistent_data = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = exposure

    w = bpy.data.worlds.new("sky")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (1.0, 0.93, 0.84, 1)
    bg.inputs["Strength"].default_value = sky

    def sun(name, elev_deg, az_deg, energy, ang, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, "SUN")
        d.energy, d.angle, d.color = energy, math.radians(ang), color
        o = bpy.data.objects.new(name, d)
        sc.collection.objects.link(o)
        e, a = math.radians(elev_deg), math.radians(az_deg)
        # a sun shines down its -Z; aim it so the light arrives from azimuth az (0 = from the front, +Y) at elevation e
        o.rotation_euler = (math.radians(90) - e, 0, math.radians(180) + a)
        return o

    sun("key", 60, 0, key, 18, (1.0, 0.96, 0.9))
    sun("rimL", 22, 145, fill, 10, (1.0, 0.88, 0.7))
    sun("rimR", 22, -145, fill, 10, (1.0, 0.88, 0.7))
    sun("bounce", 10, 0, 0.45, 40, (1.0, 0.85, 0.65))

    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho
    cam.data.clip_start, cam.data.clip_end = 1, 4000
    aim(cam, elev, target)
    sc.camera = cam
    if floor:
        me = bpy.data.meshes.new("floor")
        me.from_pydata([(-2000, -2000, 0), (2000, -2000, 0), (2000, 2000, 0), (-2000, 2000, 0)], [], [(0, 1, 2, 3)])
        fo = bpy.data.objects.new("floor", me)
        sc.collection.objects.link(fo)
        m = bpy.data.materials.new("floor")
        m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.9, 0.88, 0.84, 1)
        me.materials.append(m)
    return kind, cam


def aim(cam, elev, target, front=True):
    """Orthographic camera above the spider, leaning in `elev` degrees from the ground. front=True puts it in front of
    the spider (so the face and the eyes show) and rolls it so that +Y, the way the spider faces, is the top of the image;
    the page then turns the finished sprite to whatever heading it needs."""
    e = math.radians(elev)
    c, s = math.cos(e), math.sin(e)
    t = Vector(target)
    if front:
        cam.location = t + Vector((0, 900 * c, 900 * s))
        X, Y, Z = Vector((1, 0, 0)), Vector((0, s, -c)), Vector((0, c, s))
    else:
        cam.location = t + Vector((0, -900 * c, 900 * s))
        X, Y, Z = Vector((1, 0, 0)), Vector((0, s, c)), Vector((0, -c, s))
    from mathutils import Matrix
    cam.rotation_euler = Matrix((X, Y, Z)).transposed().to_euler()


def render(path):
    sc = bpy.context.scene
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - t
