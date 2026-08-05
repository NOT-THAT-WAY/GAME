"""Report which bones own which parts of the mesh, to find bad skin weights."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()

arm = bpy.data.objects["K3_FABLE_MASCOT"]
body = bpy.data.objects["K3_MECHA_BODY"]
gi = {g.index: g.name for g in body.vertex_groups}

stats = {}
outliers = []
for v in body.data.vertices:
    if not v.groups:
        continue
    best = max(v.groups, key=lambda g: g.weight)
    name = gi.get(best.group, "?")
    co = v.co
    s = stats.setdefault(name, {"count": 0, "min": [9, 9, 9], "max": [-9, -9, -9], "wsum": 0.0})
    s["count"] += 1
    s["wsum"] += best.weight
    for i in range(3):
        s["min"][i] = min(s["min"][i], round(co[i], 3))
        s["max"][i] = max(s["max"][i], round(co[i], 3))
    # a torso/leg vertex dominated by an arm bone is the classic blade artifact
    if "ARM" in name and (co.z < 1.15 or abs(co.x) < 0.16):
        outliers.append({"bone": name, "co": [round(c, 3) for c in co], "w": round(best.weight, 3)})

for s in stats.values():
    s["mean_dominant_weight"] = round(s["wsum"] / max(s["count"], 1), 3)
    del s["wsum"]

report = {"dominant_bone_regions": stats, "arm_bones_owning_torso_or_legs": outliers[:40],
          "outlier_count": len(outliers)}
(TRIAL / "diagnostics" / "weight-check.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps({
    "regions": {k: (v["count"], v["min"], v["max"]) for k, v in sorted(stats.items())},
    "outlier_count": len(outliers)}, ensure_ascii=False))
