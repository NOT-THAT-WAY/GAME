"""Mount the project master audio in the VSE so the .blend carries its own sound."""
import bpy
import json
from pathlib import Path

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()
FRAME_END = 360

scene = bpy.context.scene
if not scene.sequence_editor:
    scene.sequence_editor_create()
for strip in list(scene.sequence_editor.strips):
    if strip.name.startswith("K3_FABLE_AUDIO"):
        scene.sequence_editor.strips.remove(strip)

master = (TRIAL / "../../fl-studio-box-semantic-template/media/current/master.mp4").resolve()
strip = scene.sequence_editor.strips.new_sound("K3_FABLE_AUDIO", str(master), 1, 1)
strip.frame_final_end = FRAME_END + 1
scene.sync_mode = "AUDIO_SYNC"

bpy.ops.wm.save_as_mainfile(filepath=str(TRIAL / "scene" / "trial.blend"))
print("UNRECORDED_RESULT=" + json.dumps({"audio": str(master), "end": strip.frame_final_end}, ensure_ascii=False))
