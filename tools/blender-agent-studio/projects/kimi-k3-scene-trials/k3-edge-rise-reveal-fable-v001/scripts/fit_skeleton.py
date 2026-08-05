"""Fit joint positions to the mecha mascot mesh (read-only measurement).

Legs: median line of each leg per z-slice (below the crotch).
Arms: median line per |x|-slice above the shoulder height.
Writes diagnostics/skeleton-fit.json.
"""
import bpy
import json
from pathlib import Path
from mathutils import Vector

P = globals().get("UNRECORDED_PARAMS", {})
out_path = Path(P.get("output", "diagnostics/skeleton-fit.json"))

body = bpy.data.objects["K3_MECHA_BODY"]
head = bpy.data.objects["K3_MECHA_HEAD"]
verts = [body.matrix_world @ v.co for v in body.data.vertices]
zs = [v.z for v in verts]
z_lo, z_hi = min(zs), max(zs)

def centroid(pts):
    return sum(pts, Vector()) / len(pts)

# ---- find the crotch: lowest z where the two legs merge into one blob in x
leg_profile = []
for i in range(60):
    a = z_lo + (z_hi - z_lo) * i / 60.0
    b = z_lo + (z_hi - z_lo) * (i + 1) / 60.0
    band = [v for v in verts if a <= v.z < b]
    if not band:
        continue
    near_axis = [v for v in band if abs(v.x) < 0.03]
    leg_profile.append({
        "z": round((a + b) / 2, 4),
        "x_max": round(max(v.x for v in band), 4),
        "n_near_axis": len(near_axis),
        "y_mean": round(sum(v.y for v in band) / len(band), 4),
    })

crotch_z = None
for entry in leg_profile:
    if entry["n_near_axis"] > 0 and entry["z"] > 0.3:
        crotch_z = entry["z"]
        break

# ---- leg median lines (below crotch), per side
legs = {}
for side, sign in (("L", 1), ("R", -1)):
    line = []
    for i in range(26):
        a = z_lo + (crotch_z - z_lo) * i / 26.0
        b = z_lo + (crotch_z - z_lo) * (i + 1) / 26.0
        band = [v for v in verts if a <= v.z < b and sign * v.x > 0.02]
        if len(band) < 6:
            continue
        c = centroid(band)
        line.append({
            "z": round((a + b) / 2, 4),
            "cx": round(c.x, 4), "cy": round(c.y, 4),
            "radius_x": round((max(v.x for v in band) - min(v.x for v in band)) / 2, 4),
            "y_min": round(min(v.y for v in band), 4),
            "y_max": round(max(v.y for v in band), 4),
            "n": len(band),
        })
    legs[side] = line

# ---- foot footprint (lowest 15% of leg height)
feet = {}
foot_top = z_lo + 0.10 * (crotch_z - z_lo)
for side, sign in (("L", 1), ("R", -1)):
    band = [v for v in verts if v.z < foot_top and sign * v.x > 0.02]
    feet[side] = {
        "x": [round(min(v.x for v in band), 4), round(max(v.x for v in band), 4)],
        "y": [round(min(v.y for v in band), 4), round(max(v.y for v in band), 4)],
        "z_min": round(min(v.z for v in band), 5),
        "centroid": [round(c, 4) for c in centroid(band)],
    }

# ---- torso median line (above crotch, near axis in x)
torso = []
for i in range(20):
    a = crotch_z + (z_hi - crotch_z) * i / 20.0
    b = crotch_z + (z_hi - crotch_z) * (i + 1) / 20.0
    band = [v for v in verts if a <= v.z < b and abs(v.x) < 0.20]
    if len(band) < 6:
        continue
    c = centroid(band)
    torso.append({
        "z": round((a + b) / 2, 4), "cx": round(c.x, 4), "cy": round(c.y, 4),
        "x_half": round(max(abs(v.x) for v in band), 4),
        "y_half": round((max(v.y for v in band) - min(v.y for v in band)) / 2, 4),
        "n": len(band),
    })

# ---- arm median lines: slice along |x| beyond the torso half-width
arms = {}
torso_half = max(t["x_half"] for t in torso) if torso else 0.2
for side, sign in (("L", 1), ("R", -1)):
    band_all = [v for v in verts if sign * v.x > torso_half * 0.75 and v.z > crotch_z]
    if not band_all:
        arms[side] = []
        continue
    x_lo = min(sign * v.x for v in band_all)
    x_hi = max(sign * v.x for v in band_all)
    line = []
    for i in range(16):
        a = x_lo + (x_hi - x_lo) * i / 16.0
        b = x_lo + (x_hi - x_lo) * (i + 1) / 16.0
        band = [v for v in band_all if a <= sign * v.x < b]
        if len(band) < 4:
            continue
        c = centroid(band)
        line.append({
            "x": round(c.x, 4), "cy": round(c.y, 4), "cz": round(c.z, 4),
            "radius": round((max(v.z for v in band) - min(v.z for v in band)) / 2, 4),
            "n": len(band),
        })
    arms[side] = line

payload = {
    "asset_height": round(head.matrix_world.translation.z + 0.275 - z_lo, 5),
    "z_ground": round(z_lo, 5),
    "z_body_top": round(z_hi, 5),
    "head_center": [round(c, 5) for c in head.matrix_world.translation],
    "head_radius": 0.275,
    "crotch_z": crotch_z,
    "torso_half_width": round(torso_half, 4),
    "leg_profile": leg_profile,
    "legs": legs,
    "feet": feet,
    "torso": torso,
    "arms": arms,
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps({
    "asset_height": payload["asset_height"], "crotch_z": crotch_z,
    "feet": feet, "torso_top": torso[-1] if torso else None,
    "arm_L_ends": (arms["L"][0], arms["L"][-1]) if arms.get("L") else None,
}, ensure_ascii=False))
