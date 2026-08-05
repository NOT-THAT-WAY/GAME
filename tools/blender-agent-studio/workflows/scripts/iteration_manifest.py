"""Create a bounded, model-independent iteration contract without changing the scene."""
import bpy
import json
from pathlib import Path

P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
attempt = int(P.get("attempt", 1))
max_attempts = int(P.get("max_attempts", 3))
improved = bool(P.get("improved", True))
requires_taste = bool(P.get("requires_human_taste", False))
threatens_invariant = bool(P.get("threatens_invariant", False))
if requires_taste or threatens_invariant:
    disposition = "human_review"
elif attempt >= max_attempts and not improved:
    disposition = "inspect_validate"
else:
    disposition = "continue_build"

immutable = [item.strip() for item in str(P.get("immutable", "")).split(",") if item.strip()]
payload = {
    "schema_version": 1,
    "source": bpy.data.filepath,
    "scene": bpy.context.scene.name,
    "goal": str(P.get("goal", "")).strip(),
    "immutable": immutable,
    "active_category": P.get("category", "composition"),
    "attempt": attempt,
    "max_attempts": max_attempts,
    "previous_improved": improved,
    "requires_human_taste": requires_taste,
    "threatens_invariant": threatens_invariant,
    "disposition": disposition,
    "evidence": [],
}
output = Path(P["output_dir"])
output.mkdir(parents=True, exist_ok=True)
path = output / "iteration-manifest.json"
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps({"manifest": str(path), "disposition": disposition, "saved": False}, ensure_ascii=False))
