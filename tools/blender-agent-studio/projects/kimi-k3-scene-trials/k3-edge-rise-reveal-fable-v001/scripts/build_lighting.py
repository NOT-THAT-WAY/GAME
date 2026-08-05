"""Lighting + the personal idea: the room plays a note where he steps.

Light plan — the screens ARE the source. The template's own emissive panels
light the room; I only add what the white body needs to read against them:
a cool rim from the back wall to cut his silhouette out of the ramp, a soft
low fill from the camera side so he never becomes a black shape, and a very
dim warm bounce so the pearl keeps volume.

Personal idea (not in the brief): PIANO ROLL NOTES. Each time a foot lands,
the note cell under it lights up and fades, as if walking through the
sequencer triggered it. At the end, the last note stays lit under him and one
long note rises on the back wall while he looks up — the room answering him.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()
FRAME_END = 360
SCALE = 0.424

RIM_Z = 0.76
RAMP_EDGE_Y = -0.42
RAMP_ORIGIN = Vector((0.0, 0.415, 1.755))
RAMP_SLOPE = math.tan(math.radians(46.34))
RAMP_N = Vector((0.0, -0.723449, 0.690377))
RAMP_U = Vector((0.0, 0.690377, 0.723449))

def ground_z(y):
    return RIM_Z if y < RAMP_EDGE_Y else RAMP_ORIGIN.z + (y - RAMP_ORIGIN.y) * RAMP_SLOPE

scene = bpy.context.scene
root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
work = bpy.data.collections["K3_EDGE_RISE_REVEAL_FABLE_V001_WORK"]

for name in list(bpy.data.objects.keys()):
    if name.startswith(("K3_FABLE_LIGHT", "K3_FABLE_NOTE")):
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

# ---------------------------------------------------------------- lights
def add_light(name, kind, energy, color, size=1.0):
    data = bpy.data.lights.new(name + "_DATA", kind)
    data.energy = energy
    data.color = color
    if kind == "AREA":
        data.size = size
    obj = bpy.data.objects.new(name, data)
    work.objects.link(obj)
    obj.parent = root
    return obj

def aim(obj, direction):
    obj.rotation_euler = Vector(direction).normalized().to_track_quat("-Z", "Y").to_euler()

# 1. rim from behind/above: separates the white body from the bright ramp
rim = add_light("K3_FABLE_LIGHT_RIM", "AREA", 55.0, (0.62, 0.78, 1.0), size=1.6)
rim.location = (0.35, 1.05, 3.30)
aim(rim, (-0.25, -0.85, -0.95))

# 2. low fill on the camera side so he never reads as a silhouette
fill = add_light("K3_FABLE_LIGHT_FILL", "AREA", 26.0, (0.86, 0.90, 1.0), size=1.9)
fill.location = (-2.05, -1.75, 1.25)
aim(fill, (0.85, 0.95, -0.10))

# 3. dim warm bounce from the ramp itself, keeps the pearl from going flat
bounce = add_light("K3_FABLE_LIGHT_BOUNCE", "AREA", 12.0, (1.0, 0.72, 0.85), size=2.4)
bounce.location = (-0.30, -0.55, 1.05)
aim(bounce, (0.15, 0.75, 0.62))

# ---------------------------------------------------------------- notes
plan = json.loads((TRIAL / "diagnostics" / "motion-plan.json").read_text(encoding="utf-8"))
contacts = plan["contacts"]

landings = []
for side in ("L", "R"):
    rows = contacts[side]
    prev = None
    for frame, x, y, z, is_planted in rows:
        if is_planted and prev is not True and frame >= 120:
            landings.append((frame, Vector((x, y, z)), side))
        prev = is_planted

def make_note_material(name, color):
    """Emissive when lit, fully transparent when not: an unlit note must not
    read as a black rectangle painted on the floor."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for node in list(nt.nodes):
        if node.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(node)
    out = nt.nodes["Material Output"]
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = color
    emit.inputs["Strength"].default_value = 1.0
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.0
    nt.links.new(clear.outputs["BSDF"], mix.inputs[1])
    nt.links.new(emit.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    for attr, value in (("blend_method", "BLEND"), ("surface_render_method", "BLENDED"),
                        ("shadow_method", "NONE")):
        if hasattr(mat, attr):
            try:
                setattr(mat, attr, value)
            except (TypeError, AttributeError):
                pass
    return mat

note_mat = make_note_material("M_K3_NOTE", (0.55, 1.0, 0.62, 1.0))

notes = []
for i, (frame, pos, side) in enumerate(landings):
    mat = note_mat.copy()
    mat.name = f"M_K3_NOTE_{i:02d}"
    strength = mat.node_tree.nodes["Mix Shader"].inputs["Fac"]

    bpy.ops.mesh.primitive_plane_add(size=1.0)
    note = bpy.context.active_object
    note.name = f"K3_FABLE_NOTE_{i:02d}"
    for col in list(note.users_collection):
        col.objects.unlink(note)
    work.objects.link(note)
    note.parent = root
    note.data.materials.append(mat)
    note.scale = (0.16, 0.075, 1.0)

    # lie the cell flat on whichever surface the foot landed on
    on_ramp = pos.y >= RAMP_EDGE_Y
    note.rotation_euler = (math.radians(46.34) if on_ramp else 0.0, 0.0, 0.0)
    note.location = (pos.x, pos.y, ground_z(pos.y) + 0.004)

    hold = FRAME_END if i == len(landings) - 1 else frame + 26
    keys = [(max(1, frame - 2), 0.0), (frame, 1.0), (frame + 6, 0.45), (hold, 0.0)]
    if i == len(landings) - 1:
        keys = [(max(1, frame - 2), 0.0), (frame, 1.0), (frame + 6, 0.55), (FRAME_END, 0.42)]
    for fr, val in keys:
        strength.default_value = val
        strength.keyframe_insert("default_value", frame=fr)
    notes.append({"index": i, "frame": frame, "side": side,
                  "pos": [round(c, 4) for c in pos]})

# the room answers: one long note rises on the back wall while he looks up
answer_mat = make_note_material("M_K3_NOTE_ANSWER", (0.62, 0.92, 1.0, 1.0))
answer_strength = answer_mat.node_tree.nodes["Mix Shader"].inputs["Fac"]
bpy.ops.mesh.primitive_plane_add(size=1.0)
answer = bpy.context.active_object
answer.name = "K3_FABLE_NOTE_ANSWER"
for col in list(answer.users_collection):
    col.objects.unlink(answer)
work.objects.link(answer)
answer.parent = root
answer.data.materials.append(answer_mat)
answer.rotation_euler = (math.radians(90), 0, 0)
answer.location = (0.02, 1.34, 3.55)
answer.scale = (0.075, 1.0, 1.0)
for fr, val, sy in ((296, 0.0, 0.05), (312, 0.85, 0.62), (338, 0.62, 1.30), (FRAME_END, 0.5, 1.30)):
    answer_strength.default_value = val
    answer_strength.keyframe_insert("default_value", frame=fr)
    answer.scale = (0.075, sy, 1.0)
    answer.keyframe_insert("scale", frame=fr)

scene.render.engine = "BLENDER_EEVEE"
if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
    scene.eevee.taa_render_samples = 32

manifest = {
    "schema_version": 1,
    "trial_id": "k3-edge-rise-reveal-fable-v001",
    "principle": "les ecrans du template sont la source principale ; les ajouts servent uniquement a detacher le corps blanc",
    "lights": [
        {"name": "K3_FABLE_LIGHT_RIM", "role": "rim froid depuis le mur arriere, decoupe la silhouette sur la rampe", "energy_w": 55.0},
        {"name": "K3_FABLE_LIGHT_FILL", "role": "fill bas cote camera, empeche la silhouette de virer au noir", "energy_w": 26.0},
        {"name": "K3_FABLE_LIGHT_BOUNCE", "role": "rebond chaud tres faible de la rampe, garde le volume du pearl", "energy_w": 12.0},
    ],
    "personal_idea": {
        "name": "PIANO ROLL NOTES",
        "description": "chaque pose de pied allume la cellule de note sous lui puis s'eteint ; la derniere reste allumee et le mur arriere repond par une note tenue pendant qu'il leve les yeux",
        "note_count": len(notes),
        "notes": notes,
        "answer_note": "K3_FABLE_NOTE_ANSWER, frames 296-360",
    },
}
(TRIAL / "gates" / "lighting-manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

bpy.ops.wm.save_as_mainfile(filepath=str(TRIAL / "scene" / "trial.blend"))
print("UNRECORDED_RESULT=" + json.dumps({"lights": 3, "notes": len(notes), "saved": True}, ensure_ascii=False))
