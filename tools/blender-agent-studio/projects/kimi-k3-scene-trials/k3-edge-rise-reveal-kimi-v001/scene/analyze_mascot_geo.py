"""Analyse la géométrie du mascot pour placer les os du rig (centres des membres)."""
import bpy, json
from mathutils import Vector

body = bpy.data.objects["K3_MECHA_BODY"]
mw = body.matrix_world
verts = [mw @ v.co for v in body.data.vertices]

def centroid(sel):
    if not sel: return None
    c = Vector((0,0,0))
    for v in sel: c += v
    return list(c/len(sel)), len(sel)

out = {}
# Bras : tranches en X (bras droit x>0)
arm = {}
for x0, x1, tag in [(0.35,0.55,"shoulder"),(0.55,0.75,"upper"),(0.75,0.95,"fore"),(0.95,2.0,"tip")]:
    sel = [v for v in verts if x0 < abs(v.x) <= x1 and v.z > 1.0]
    right = centroid([v for v in sel if v.x>0]); left = centroid([v for v in sel if v.x<0])
    arm[tag] = {"R": right, "L": left}
out["arm_slices"] = arm

# Jambes : tranches en Z
leg = {}
for z0, z1, tag in [(0.55,0.75,"hip"),(0.35,0.55,"knee"),(0.0,0.35,"shin"),(0.0,0.10,"foot")]:
    sel = [v for v in verts if z0 < v.z <= z1 and abs(v.x) < 0.6]
    right = centroid([v for v in sel if v.x>0.03]); left = centroid([v for v in sel if v.x<-0.03])
    leg[tag] = {"R": right, "L": left}
out["leg_slices"] = leg

# Torse : tranches Z
torso = {}
for z0, z1, tag in [(0.7,0.9,"pelvis"),(0.9,1.1,"waist"),(1.1,1.3,"chest"),(1.3,1.5,"neck")]:
    sel = [v for v in verts if z0 < v.z <= z1 and abs(v.x) < 0.5]
    torso[tag] = centroid(sel)
out["torso_slices"] = torso

# Tête
head = bpy.data.objects["K3_MECHA_HEAD"]
hv = [head.matrix_world @ v.co for v in head.data.vertices]
hc = centroid(hv)
out["head"] = {"centroid": hc, "z_min": min(v.z for v in hv), "z_max": max(v.z for v in hv)}
# corps z max (cou)
out["body_z_max"] = max(v.z for v in verts)
out["body_z_min"] = min(v.z for v in verts)

print("GEO_JSON=" + json.dumps(out, indent=1))
