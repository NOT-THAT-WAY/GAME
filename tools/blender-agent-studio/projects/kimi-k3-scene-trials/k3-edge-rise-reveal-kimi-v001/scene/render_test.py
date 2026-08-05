import bpy, os, sys
sc = bpy.context.scene
outdir = os.path.join(os.path.dirname(bpy.data.filepath), "..", "gates", "test")
os.makedirs(outdir, exist_ok=True)
sc.render.resolution_x = 640
sc.render.resolution_y = 360
frames = [int(a) for a in sys.argv[sys.argv.index("--")+1:]] if "--" in sys.argv else [1]
for f in frames:
    sc.frame_set(f)
    sc.render.filepath = os.path.join(outdir, f"test_f{f:03d}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", f)
