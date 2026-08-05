import bpy, json

scenes = []
for scene in bpy.data.scenes:
    scenes.append({
        "name": scene.name,
        "objects": len(scene.objects),
        "frame_range": [scene.frame_start, scene.frame_end],
        "fps": scene.render.fps / scene.render.fps_base if scene.render.fps_base else None,
        "fps_numerator": scene.render.fps,
        "fps_base": scene.render.fps_base,
        "engine": scene.render.engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "camera": scene.camera.name if scene.camera else None,
        "markers": [{"name": marker.name, "frame": marker.frame} for marker in scene.timeline_markers],
    })

payload = {
    "file": bpy.data.filepath,
    "active_scene": bpy.context.scene.name,
    "scenes": scenes,
    "collections": [{"name": col.name, "objects": len(col.objects)} for col in bpy.data.collections],
    "cameras": [obj.name for obj in bpy.data.objects if obj.type == "CAMERA"],
    "materials": len(bpy.data.materials),
    "actions": len(bpy.data.actions),
    "dirty": bpy.data.is_dirty,
}
print("UNRECORDED_RESULT=" + json.dumps(payload, ensure_ascii=False))
