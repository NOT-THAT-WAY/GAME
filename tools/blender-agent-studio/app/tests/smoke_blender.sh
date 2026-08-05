#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BLENDER="${BLENDER_BIN:-/Applications/Blender.app/Contents/MacOS/Blender}"
FIXTURE_SCRIPT="$ROOT/app/tests/create_blender_fixture.py"
CAMERA="$ROOT/workflows/scripts/camera_workflow.py"
HOVER="$ROOT/workflows/scripts/hover_loop.py"
SHOT="$ROOT/workflows/scripts/build_camera_shot.py"
AUDIT="$ROOT/workflows/scripts/deep_audit_scene.py"
VIEW_DIAG="$ROOT/workflows/scripts/scene_view_diagnostics.py"
ITERATION="$ROOT/workflows/scripts/iteration_manifest.py"
SPATIAL="$ROOT/workflows/scripts/scene_spatial_graph.py"
LIGHTING="$ROOT/workflows/scripts/studio_lighting.py"
LIGHTING_GATE="$ROOT/workflows/scripts/drumboiii_lighting_gate.py"
RENDER="$ROOT/workflows/scripts/render_keyframes.py"
EXPORT="$ROOT/workflows/scripts/export_glb.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
FILE="$TMP/team-studio-fixture.blend"

"$BLENDER" --factory-startup --background --disable-autoexec --python "$FIXTURE_SCRIPT" -- "$FILE" \
  2>&1 | grep -q 'SMOKE_FIXTURE='
test -s "$FILE"

for pattern in orbit-360 lowrise-orbit arc-crane-vertigo; do
  "$BLENDER" --background --disable-autoexec "$FILE" --python-expr \
    "STUDIO_PARAMS={'pattern':'$pattern','duration':2,'intensity':1,'distance':8,'lens':60,'direction':'gauche','target_collection':'SMOKE_STAGE'}; exec(compile(open('$CAMERA').read(), '$CAMERA', 'exec'))" \
    2>&1 | grep -q 'UNRECORDED_RESULT='
done
"$BLENDER" --background --disable-autoexec "$FILE" --python-expr \
  "STUDIO_PARAMS={'collection':'SMOKE_STAGE','duration':2,'bob':0.1,'yaw':3,'cause':'zero_gravity','cause_evidence':'contract:smoke-test'}; exec(compile(open('$HOVER').read(), '$HOVER', 'exec'))" \
  2>&1 | grep -q 'UNRECORDED_RESULT='
"$BLENDER" --background --disable-autoexec "$FILE" --python-expr \
  "STUDIO_PARAMS={'job_id':'smoketest','output_dir':'$TMP/shot','template':'dolly-reveal','duration':2,'lens':60,'distance_multiplier':4,'direction':'gauche','target_collection':'SMOKE_STAGE'}; exec(compile(open('$SHOT').read(), '$SHOT', 'exec'))" \
  2>&1 | grep -q 'UNRECORDED_RESULT='
test -f "$TMP/shot/shot-manifest.json"
"$BLENDER" --background --disable-autoexec "$FILE" --python-expr \
  "STUDIO_PARAMS={'output_dir':'$TMP/audit','include_nodes':True}; exec(compile(open('$AUDIT').read(), '$AUDIT', 'exec'))" \
  2>&1 | grep -q 'UNRECORDED_RESULT='
test -f "$TMP/audit/scene-audit.json"
"$BLENDER" --background --disable-autoexec "$FILE" --python-expr \
  "STUDIO_PARAMS={'output_dir':'$TMP/view','collection':'SMOKE_STAGE','camera':'','frame':1}; exec(compile(open('$VIEW_DIAG').read(), '$VIEW_DIAG', 'exec'))" \
  2>&1 | grep -q 'UNRECORDED_RESULT='
test -f "$TMP/view/scene-view-diagnostics.json"
"$BLENDER" --background --disable-autoexec "$FILE" --python-expr \
  "STUDIO_PARAMS={'output_dir':'$TMP/iteration','goal':'keep subject readable','immutable':'scale,function','category':'composition','attempt':3,'max_attempts':3,'improved':False,'requires_human_taste':False,'threatens_invariant':False}; exec(compile(open('$ITERATION').read(), '$ITERATION', 'exec'))" \
  2>&1 | grep -q 'UNRECORDED_RESULT='
test -f "$TMP/iteration/iteration-manifest.json"
grep -q 'inspect_validate' "$TMP/iteration/iteration-manifest.json"
"$BLENDER" --background --disable-autoexec "$FILE" --python-expr \
  "STUDIO_PARAMS={'output_dir':'$TMP/spatial','collection':'SMOKE_STAGE','max_objects':80,'relation_distance':0.25}; exec(compile(open('$SPATIAL').read(), '$SPATIAL', 'exec'))" \
  2>&1 | grep -q 'UNRECORDED_RESULT='
test -f "$TMP/spatial/scene-spatial-graph.json"
"$BLENDER" --background --disable-autoexec "$FILE" --python-expr \
  "STUDIO_PARAMS={'preset':'softbox-product','target_collection':'SMOKE_STAGE','intensity':1.0,'mute_existing_lights':True,'view_transform':'AgX'}; exec(compile(open('$LIGHTING').read(), '$LIGHTING', 'exec'))" \
  2>&1 | grep -q 'UNRECORDED_RESULT='
"$BLENDER" --background --disable-autoexec "$FILE" --python-expr \
  "STUDIO_PARAMS={'preset':'drumboiii-layered','target_collection':'SMOKE_STAGE','intensity':1.0,'mute_existing_lights':True,'configure_world':True,'world_strength':0.7,'visible_world_strength':0.35,'render_engine':'BLENDER_EEVEE_NEXT'}; exec(compile(open('$LIGHTING').read(), '$LIGHTING', 'exec')); STUDIO_PARAMS={'output_dir':'$TMP/drumboiii-lighting','frame':1,'resolution_percentage':10,'samples':1}; exec(compile(open('$LIGHTING_GATE').read(), '$LIGHTING_GATE', 'exec'))" \
  2>&1 | grep -q 'UNRECORDED_RESULT='
test -f "$TMP/drumboiii-lighting/lighting-gate-manifest.json"
test "$(find "$TMP/drumboiii-lighting" -name '*.png' | wc -l | tr -d ' ')" = "6"
"$BLENDER" --background --disable-autoexec "$FILE" --python-expr \
  "STUDIO_PARAMS={'output_dir':'$TMP/render','resolution_x':64,'resolution_y':64,'samples':1,'engine':'BLENDER_EEVEE_NEXT'}; exec(compile(open('$RENDER').read(), '$RENDER', 'exec'))" \
  2>&1 | grep -q 'UNRECORDED_RESULT='
test -f "$TMP/render/manifest.json"
test "$(find "$TMP/render" -name 'frame_*.png' | wc -l | tr -d ' ')" -ge "3"
"$BLENDER" --background --disable-autoexec "$FILE" --python-expr \
  "STUDIO_PARAMS={'output_dir':'$TMP/export','collection':'SMOKE_ASSET','apply_modifiers':True}; exec(compile(open('$EXPORT').read(), '$EXPORT', 'exec'))" \
  2>&1 | grep -q 'UNRECORDED_RESULT='
test -s "$TMP/export/smoke_asset.glb"
"$BLENDER" --factory-startup --background --disable-autoexec --python-expr \
  "import bpy; bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False); bpy.ops.import_scene.gltf(filepath='$TMP/export/smoke_asset.glb'); meshes=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']; assert len(meshes)==2; print('GLB_REIMPORT_OK=2')" \
  2>&1 | grep -q 'GLB_REIMPORT_OK=2'
echo "Blender synthetic workflow smoke: OK"
