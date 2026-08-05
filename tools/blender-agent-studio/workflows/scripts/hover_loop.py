import bpy, json, math
from mathutils import Vector

P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
scene = bpy.context.scene
collection_name = P.get("collection", "AUTO")
cause = str(P.get("cause", "")).strip()
cause_evidence = str(P.get("cause_evidence", "")).strip()
if cause not in {"visible_rig", "magnetic_field", "zero_gravity"}:
    raise RuntimeError("Une cause explicite est requise: visible_rig, magnetic_field ou zero_gravity")
if not cause_evidence:
    raise RuntimeError("cause_evidence est requis et doit pointer vers un objet visible ou un contrat")
if cause in {"visible_rig", "magnetic_field"} and not bpy.data.objects.get(cause_evidence):
    raise RuntimeError("Objet de preuve de la cause introuvable: " + cause_evidence)
if cause == "zero_gravity" and not cause_evidence.startswith("contract:"):
    raise RuntimeError("zero_gravity exige cause_evidence=contract:<référence>")
direct = None
roots = []
if collection_name.upper() == "AUTO":
    selected_roots = []
    for selected in bpy.context.selected_objects:
        root = selected
        while root.parent:
            root = root.parent
        if root not in selected_roots:
            selected_roots.append(root)
    if len(selected_roots) == 1:
        direct = selected_roots[0]
    elif selected_roots:
        roots = selected_roots
    else:
        direct = next((bpy.data.objects.get(name) for name in ("flroom_device_pivot", "choreo_device_pivot") if bpy.data.objects.get(name) in scene.objects[:]), None)
    roots = [direct] if direct else roots
else:
    collection = bpy.data.collections.get(collection_name)
    if not collection:
        raise RuntimeError("Collection introuvable: " + collection_name)
    roots = [obj for obj in collection.objects if obj.parent is None and obj.name not in {"BAS_HOVER_CONTROL", "ustudio_hover_control"} and obj in scene.objects[:]]
if not roots:
    raise RuntimeError("Aucune cible animable dans la scène active")

if direct:
    control = direct
    control.animation_data_clear()
else:
    control = bpy.data.objects.get("BAS_HOVER_CONTROL")
    if not control:
        control = bpy.data.objects.new("BAS_HOVER_CONTROL", None)
        scene.collection.objects.link(control)
    points = [obj.matrix_world.translation for obj in roots]
    control.location = sum(points, Vector()) / len(points)
    control.animation_data_clear()
    for obj in roots:
        world = obj.matrix_world.copy()
        obj.parent = control
        obj.matrix_world = world

if "fps" in P:
    fps = int(P["fps"])
    scene.render.fps = fps
    scene.render.fps_base = 1.0
else:
    fps = scene.render.fps / scene.render.fps_base if scene.render.fps_base else float(scene.render.fps)
duration = float(P.get("duration", 10))
frames = max(2, round(duration * fps))
bob = float(P.get("bob", .7))
yaw = math.radians(float(P.get("yaw", 6)))
scene.frame_start, scene.frame_end = 1, frames
base = control.location.copy()
for frame in range(1, frames + 1):
    t = (frame - 1) / (frames - 1)
    control.location = base + Vector((.35*math.sin(2*math.pi*t), .2*math.sin(4*math.pi*t+.7), bob*math.sin(4*math.pi*t)))
    control.rotation_euler = (math.radians(2)*math.sin(4*math.pi*t+.3), math.radians(1.5)*math.sin(2*math.pi*t+.9), yaw*math.sin(2*math.pi*t))
    control.keyframe_insert("location", frame=frame)
    control.keyframe_insert("rotation_euler", frame=frame)
scene.frame_set(1)
print("UNRECORDED_RESULT=" + json.dumps({"workflow":"hover-loop","collection":collection_name,"frames":frames,"fps":fps,"roots":[o.name for o in roots],"cause":cause,"cause_evidence":cause_evidence,"physical_validation_required":True,"saved":False}))
