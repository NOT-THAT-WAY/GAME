"""Caméra diagnostique latérale + rendus de profil pour vérifier l'anatomie."""
import bpy, os, sys
from mathutils import Vector
sc = bpy.context.scene
cam = bpy.data.objects.get("K3_EDGE_DIAG_SIDE")
if cam is None:
    cd = bpy.data.cameras.new("K3_EDGE_DIAG_SIDE")
    cam = bpy.data.objects.new("K3_EDGE_DIAG_SIDE", cd)
    sc.collection.objects.link(cam)
    cd.lens = 45
cam.location = (-3.4, -1.2, 2.3)
d = (Vector((0, -0.55, 2.3)) - Vector(cam.location)).normalized()
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
old = sc.camera
sc.camera = cam
outdir = os.path.join(os.path.dirname(bpy.data.filepath), "..", "gates", "test")
frames = [int(a) for a in sys.argv[sys.argv.index("--")+1:]] if "--" in sys.argv else [100]
for f in frames:
    sc.frame_set(f)
    sc.render.filepath = os.path.join(outdir, f"side_f{f:03d}.png")
    bpy.ops.render.render(write_still=True)
    print("SIDE", f)
sc.camera = old
bpy.ops.wm.save_mainfile()
