# Independent reimport gate: open the candidate FBX in a genuinely empty Blender
# scene and verify it against the master .blend, per frame.
#
# A Blender reimport is NOT a target-engine import; this only proves the file
# round-trips. The Unity gate is separate.
#
# Usage:
#   blender -b --factory-startup --python reimport_verify_sb_idle.py -- <master.blend> <candidate.fbx> <out.json>

import bpy, sys, json, math, re, struct
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
MASTER, CAND, OUT = argv[0], argv[1], argv[2]


def raw_fbx_take_names(path):
    """AnimStack names read straight from the FBX binary.

    Blender's IMPORTER renames actions to '<object>|<take>', so the reimported
    action name is NOT evidence of what the file stores. FBX binary stores an
    object name as a length-prefixed '<name>\\x00\\x01<Class>' string, so for each
    '\\x00\\x01AnimStack' we scan backwards for the uint32 length field that
    exactly spans the string.

    Control-tested against the source FBX, where it correctly recovers
    'BAS_PUNCH_Rig|BAS_PUNCH_punch'.
    """
    blob = open(path, "rb").read()
    names = []
    tag = b"\x00\x01AnimStack"
    for m in re.finditer(re.escape(tag), blob):
        end = m.start() + len(tag)
        for s in range(m.start(), max(0, m.start() - 256), -1):
            if s - 4 < 0:
                break
            (ln,) = struct.unpack("<I", blob[s - 4:s])
            if ln == end - s:
                names.append(blob[s:m.start()].decode("utf-8", "replace"))
                break
    return sorted(set(names))

EXPECTED_BONES = [
    "BAS_PUNCH_root", "BAS_PUNCH_body",
    "BAS_PUNCH_upperarm.L", "BAS_PUNCH_forearm.L", "BAS_PUNCH_hand.L",
    "BAS_PUNCH_upperarm.R", "BAS_PUNCH_forearm.R", "BAS_PUNCH_hand.R",
    "BAS_PUNCH_foot.L", "BAS_PUNCH_foot.R",
]


def action_fcurves(a):
    if hasattr(a, "fcurves"):
        return list(a.fcurves)
    out = []
    for layer in a.layers:
        for strip in layer.strips:
            for cb in getattr(strip, "channelbags", []):
                out.extend(cb.fcurves)
    return out


def sample(scene_frames):
    """Per-frame world matrices of every bone + evaluated bounds."""
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    out = {}
    bounds = {}
    for f in scene_frames:
        bpy.context.scene.frame_set(f)
        out[f] = {pb.name: (arm.matrix_world @ pb.matrix).copy() for pb in arm.pose.bones}
        dg = bpy.context.evaluated_depsgraph_get()
        lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
        for o in bpy.data.objects:
            if o.type != "MESH":
                continue
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            for v in me.vertices:
                w = ev.matrix_world @ v.co
                for i in range(3):
                    lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
            ev.to_mesh_clear()
        bounds[f] = (lo.copy(), hi.copy())
    return out, bounds


# ------------------------------------------------------------ master reference
bpy.ops.wm.open_mainfile(filepath=MASTER)
FRAMES = list(range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1))
master_mats, master_bounds = sample(FRAMES)

# ------------------------------------------------------------ candidate import
bpy.ops.wm.read_factory_settings(use_empty=True)
for coll in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights,
             bpy.data.materials, bpy.data.armatures, bpy.data.actions):
    for db in list(coll):
        coll.remove(db)
bpy.ops.import_scene.fbx(filepath=CAND)

sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.data.objects if o.type == "MESH"]

rep = {"master_blend": MASTER, "candidate_fbx": CAND,
       "scene_state": "read_factory_settings(use_empty=True) + orphan purge"}

# ---- structural census ----
rep["census"] = {
    "object_types": sorted({o.type for o in bpy.data.objects}),
    "mesh_objects": len(meshes),
    "armature_objects": len([o for o in bpy.data.objects if o.type == "ARMATURE"]),
    "cameras": [c.name for c in bpy.data.cameras],
    "lights": [l.name for l in bpy.data.lights],
    "unskinned_meshes": [o.name for o in meshes
                         if not any(m.type == "ARMATURE" for m in o.modifiers)],
    "actions": [a.name for a in bpy.data.actions],
    "total_vertices": sum(len(o.data.vertices) for o in meshes),
    "total_tris": sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes),
}
rep["census"]["no_parasites"] = (
    rep["census"]["object_types"] == ["ARMATURE", "MESH"]
    and not rep["census"]["cameras"] and not rep["census"]["lights"]
    and not rep["census"]["unskinned_meshes"])

# ---- skeleton ----
got = [b.name for b in arm.data.bones]
hierarchy = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}
rep["skeleton"] = {
    "bone_count": len(got),
    "bones": got,
    "names_match_source": sorted(got) == sorted(EXPECTED_BONES),
    "missing": [b for b in EXPECTED_BONES if b not in got],
    "unexpected": [b for b in got if b not in EXPECTED_BONES],
    "hierarchy": hierarchy,
    "leaf_bones_added": [b for b in got if b.endswith("_end")],
    "armature_object_transform": {
        "location": [round(v, 6) for v in arm.location],
        "rotation_deg": [round(math.degrees(v), 4) for v in arm.rotation_euler],
        "scale": [round(v, 6) for v in arm.scale],
    },
}

# ---- action / clip ----
acts = list(bpy.data.actions)
rep["clip"] = {"action_count": len(acts)}
if acts:
    a = acts[0]
    fr = a.frame_range
    ch = set()
    for fc in action_fcurves(a):
        if fc.data_path.startswith('pose.bones["'):
            ch.add(fc.data_path.split('"')[1])
    raw_names = raw_fbx_take_names(CAND)
    # Blender's importer prefixes actions with '<object>|'. Strip it to recover
    # the take name the file actually stores; cross-check against the binary.
    stripped = a.name.split("|")[-1]
    rep["clip"].update({
        "name_after_blender_import": a.name,
        "blender_importer_prefix_note": ("Blender's FBX importer names actions "
                                         "'<object>|<take>'; the take itself is the "
                                         "part after the last '|'"),
        "take_name_stripped": stripped,
        "raw_fbx_anim_stack_names": raw_names,
        "raw_fbx_take_count": len(raw_names),
        "name_is_exactly_SB_Idle": (stripped == "SB_Idle"
                                    and raw_names == ["SB_Idle"]),
        "frame_start": round(fr[0], 4),
        "frame_end": round(fr[1], 4),
        "frame_span": round(fr[1] - fr[0], 4),
        "span_is_59_intervals_60_samples": abs((fr[1] - fr[0]) - 59.0) < 1e-6,
        "range_is_1_to_60": abs(fr[0] - 1.0) < 1e-6 and abs(fr[1] - 60.0) < 1e-6,
        "fcurve_count": len(action_fcurves(a)),
        "bones_animated": sorted(ch),
        "all_10_bones_animated": len(ch) == 10,
        "scene_fps": sc.render.fps / sc.render.fps_base,
        "fps_is_30": abs(sc.render.fps / sc.render.fps_base - 30.0) < 1e-6,
        "duration_s": round((fr[1] - fr[0]) / (sc.render.fps / sc.render.fps_base), 6),
    })
    # The Punch placeholder must not have been exported. Test for the punch
    # ACTION, not the substring "punch" - every bone carries the BAS_PUNCH_
    # prefix, so a substring test is a guaranteed false positive.
    blob = open(CAND, "rb").read()
    rep["clip"]["punch_absent"] = (
        len(acts) == 1
        and b"BAS_PUNCH_punch" not in blob
        and not any(x.name.split("|")[-1] == "BAS_PUNCH_punch" for x in acts))

# ---- per-frame comparison against the master ----
# Blender's FBX round-trip can renumber the action (the importer maps the take's
# time span onto its own start frame). That is a NUMBERING convention, not motion
# drift, so the comparison is run at several offsets and the best alignment is
# reported together with the offset it needed.
sc.frame_start, sc.frame_end = 1, 62
cand_mats, cand_bounds = sample(list(range(1, 63)))

offsets = {}
for k in (0, 1, -1):
    wt, wr, wb, wtf, wbone = 0.0, 0.0, 0.0, None, None
    ok = True
    for f in FRAMES:
        g = f + k
        if g not in cand_mats:
            ok = False
            break
        for bn in EXPECTED_BONES:
            mm, cm = master_mats[f][bn], cand_mats[g][bn]
            dt = (mm.translation - cm.translation).length
            dr = math.degrees(mm.to_quaternion().rotation_difference(
                cm.to_quaternion()).angle)
            if dt > wt:
                wt, wtf, wbone = dt, f, bn
            wr = max(wr, dr)
        ml, mh = master_bounds[f]
        cl, chh = cand_bounds[g]
        wb = max(wb, (ml - cl).length, (mh - chh).length)
    if ok:
        offsets[k] = {"max_bone_translation_delta_m": round(wt, 8),
                      "max_bone_rotation_delta_deg": round(wr, 6),
                      "max_evaluated_bounds_delta_m": round(wb, 8),
                      "worst_translation_frame": wtf,
                      "worst_translation_bone": wbone}

best_k = min(offsets, key=lambda k: offsets[k]["max_bone_translation_delta_m"])
best = offsets[best_k]
rep["master_vs_candidate"] = {
    "frames_compared": len(FRAMES),
    "tested_frame_offsets": {str(k): v for k, v in offsets.items()},
    "best_frame_offset": best_k,
    "offset_meaning": ("candidate scene frame (master frame + offset) holds the same "
                       "pose; a non-zero offset is a frame-numbering convention of "
                       "Blender's FBX importer, not motion drift"),
    "max_bone_translation_delta_m": best["max_bone_translation_delta_m"],
    "worst_translation_frame": best["worst_translation_frame"],
    "worst_translation_bone": best["worst_translation_bone"],
    "max_bone_rotation_delta_deg": best["max_bone_rotation_delta_deg"],
    "max_evaluated_bounds_delta_m": best["max_evaluated_bounds_delta_m"],
    "matches": (best["max_bone_translation_delta_m"] < 1e-4
                and best["max_bone_rotation_delta_deg"] < 0.05
                and best["max_evaluated_bounds_delta_m"] < 1e-4),
}

# ---- root immobility in the reimported file ----
rootname = "BAS_PUNCH_root"
rt, rr = 0.0, 0.0
rest = arm.data.bones[rootname].matrix_local
for f in cand_mats:
    m = cand_mats[f][rootname]
    rt = max(rt, (m.translation - (arm.matrix_world @ rest).translation).length)
    rr = max(rr, math.degrees(
        m.to_quaternion().rotation_difference((arm.matrix_world @ rest).to_quaternion()).angle))
rep["root_motion_after_reimport"] = {
    "bone": rootname,
    "max_translation_m": round(rt, 8),
    "max_rotation_deg": round(rr, 6),
    "passed": rt < 1e-6 and rr < 1e-4,
}

# ---- weights survived ----
maxinf, unw = 0, 0
for o in meshes:
    deform = {b.name for b in arm.data.bones if b.use_deform}
    gi = {g.index: g.name for g in o.vertex_groups}
    di = {i for i, n in gi.items() if n in deform}
    for v in o.data.vertices:
        gs = [g for g in v.groups if g.group in di and g.weight > 1e-6]
        maxinf = max(maxinf, len(gs))
        if not gs:
            unw += 1
rep["weights_after_reimport"] = {"max_influences": maxinf, "unweighted_vertices": unw,
                                 "within_4_influence_budget": maxinf <= 4 and unw == 0}

rep["passed"] = all([
    rep["census"]["no_parasites"],
    rep["skeleton"]["names_match_source"],
    not rep["skeleton"]["leaf_bones_added"],
    rep["clip"].get("name_is_exactly_SB_Idle", False),
    rep["clip"].get("span_is_59_intervals_60_samples", False),
    rep["clip"].get("fps_is_30", False),
    rep["clip"].get("all_10_bones_animated", False),
    rep["clip"].get("punch_absent", False),
    rep["master_vs_candidate"]["matches"],
    rep["root_motion_after_reimport"]["passed"],
    rep["weights_after_reimport"]["within_4_influence_budget"],
])

with open(OUT, "w") as fh:
    json.dump(rep, fh, indent=2)
print("REIMPORT_WRITTEN " + OUT + " passed=" + str(rep["passed"]))
