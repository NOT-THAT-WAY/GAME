"""Mesures détaillées : pente piano roll (verts réels), rim top, cycle playhead, audio."""
import bpy, json, math, os
from mathutils import Vector

sc = bpy.context.scene
out = {}

def mesh_world_verts(name):
    o = bpy.data.objects[name]
    return [o.matrix_world @ v.co for v in o.data.vertices]

# --- Piano roll : plan réel ---
vs = mesh_world_verts("USTUDIO_PIANO_ROLL_FLOOR")
xs = [v.x for v in vs]; ys=[v.y for v in vs]; zs=[v.z for v in vs]
# 4 coins : combinaisons extremes y/z
low  = min(vs, key=lambda v: v.z)
high = max(vs, key=lambda v: v.z)
uphill = (Vector((0, high.y, high.z)) - Vector((0, low.y, low.z)))
uphill_n = uphill.normalized()
slope = math.degrees(math.asin(uphill_n.z))
normal = Vector((0, -uphill_n.z, uphill_n.y))  # perpendiculaire dans plan YZ, vers le devant/haut
out["piano_roll"] = {
    "n_verts": len(vs),
    "x_range": [min(xs), max(xs)],
    "y_range": [min(ys), max(ys)],
    "z_range": [min(zs), max(zs)],
    "low_corner": list(low), "high_corner": list(high),
    "slope_deg": slope,
    "uphill_tangent": list(uphill_n),
    "surface_normal": list(normal),
    "slope_length": uphill.length,
    "all_verts": [[round(v.x,4),round(v.y,4),round(v.z,4)] for v in vs[:12]],
}

# --- Rim bottom : surface d'assise ---
vs = mesh_world_verts("USTUDIO_FRONT_BOTTOM_RIM")
top = max(v.z for v in vs)
top_verts = [v for v in vs if abs(v.z-top) < 0.01]
out["bottom_rim"] = {
    "top_z": top,
    "top_y_range": [min(v.y for v in top_verts), max(v.y for v in top_verts)],
    "x_range": [min(v.x for v in vs), max(v.x for v in vs)],
    "z_range": [min(v.z for v in vs), max(v.z for v in vs)],
    "y_range": [min(v.y for v in vs), max(v.y for v in vs)],
}

# --- Ceiling ---
vs = mesh_world_verts("USTUDIO_CEILING")
out["ceiling_zmin"] = min(v.z for v in vs)

# --- Playhead fcurves ---
for name in ("USTUDIO_PLAYHEAD_BACK", "USTUDIO_PLAYHEAD_FLOOR"):
    o = bpy.data.objects[name]
    ad = o.animation_data
    info = {"base_loc": list(o.location)}
    curves = []
    if ad and ad.action:
        for layer in ad.action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    for fc in cb.fcurves:
                        pts = [(round(k.co.x,1), round(k.co.y,4)) for k in fc.keyframe_points]
                        curves.append({"path": fc.data_path, "idx": fc.array_index, "keys": pts})
    info["curves"] = curves
    # positions évaluées à quelques frames
    samples = {}
    for f in (1, 50, 100, 150, 203, 250, 300, 348, 360, 406):
        sc.frame_set(f)
        samples[f] = list(o.matrix_world.translation)
    info["world_pos_samples"] = samples
    out[name] = info

# --- Float root bob amplitude ---
o = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
bob = {}
for f in (1, 50, 100, 150, 203, 250, 300, 348, 406):
    sc.frame_set(f)
    bob[f] = list(o.matrix_world.translation)
out["float_root_pos"] = bob

# --- Audio dispo ---
master = os.path.join(os.path.dirname(bpy.data.filepath), "media", "current", "master.mp4")
out["master_audio_exists"] = os.path.exists(master)
out["master_audio_path"] = master
out["scene_fps"] = sc.render.fps

print("MEASURE_JSON=" + json.dumps(out, indent=1))
