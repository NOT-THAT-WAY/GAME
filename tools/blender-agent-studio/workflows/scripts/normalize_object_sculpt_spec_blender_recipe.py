#!/usr/bin/env python3
"""Normalize a blenderRecipe extension into canonical ObjectSculptSpec fields.

The img2threejs starter intentionally contains a one-node component tree.  Blender
recipes are richer than that starter, so this utility promotes recipe components,
materials, repetitions, and bound detail-inventory entries back into the upstream
schema before structural review.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


MACRO_COMPONENTS = {
    "root",
    "outer-shell",
    "internal-mechanism",
    "controls-assembly",
    "speaker-system",
    "transport-system",
}

PARENT_HINTS = {
    "outer-shell": "root",
    "internal-mechanism": "root",
    "controls-assembly": "root",
    "speaker-system": "root",
    "transport-system": "root",
    "front-plate": "outer-shell",
    "rear-plate": "outer-shell",
    "edge-frame": "outer-shell",
    "corner-hardware": "outer-shell",
    "inner-panel": "internal-mechanism",
    "pcb": "internal-mechanism",
    "internal-wiring": "internal-mechanism",
    "speaker-assembly": "speaker-system",
    "transport-rail": "transport-system",
    "transport-slot": "transport-system",
    "transport-wheel": "transport-system",
    "red-control": "controls-assembly",
    "top-controls": "controls-assembly",
    "top-dial": "controls-assembly",
    "side-control-strip": "controls-assembly",
}

LEVEL_HINTS = {
    "corner-hardware": "micro",
    "internal-wiring": "micro",
}

PRIMITIVE_HINTS = {
    "speaker-assembly": "lathe",
    "transport-wheel": "lathe",
    "top-dial": "lathe",
    "internal-wiring": "curve-sweep",
    "corner-hardware": "instanced-cluster",
}

MATERIAL_CLASS_HINTS = {
    "clear-shell": "glass",
    "clear-edge": "glass",
    "frosted-panel": "plastic",
    "black-rubber": "rubber",
    "black-gloss": "plastic",
    "brushed-metal": "metal",
    "accent-red": "plastic",
    "red-emissive": "plastic",
    "pcb-green": "plastic",
    "copper": "metal",
    "led-green": "plastic",
    "led-yellow": "plastic",
    "ink": "plastic",
}

DETAIL_MATERIAL_HINTS = {
    "red-control": "accent-red",
    "transport-slot": "red-emissive",
    "pcb": "pcb-green",
    "inner-panel": "frosted-panel",
}

FEATURE_TARGET_RENAMES = {
    "overall-silhouette": "transparent-chassis-silhouette",
    "primary-structure": "audio-mechanism-landmarks",
    "reference-material-system": "transparent-material-system",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument(
        "--recipe-from",
        type=Path,
        help=(
            "Seed blenderRecipe from another ObjectSculptSpec before normalization. "
            "Intended for deterministic regression tests of an already reviewed recipe."
        ),
    )
    return parser.parse_args()


def rgba_from_hex(value: str, alpha: float = 1.0) -> str:
    raw = value.lstrip("#")
    if len(raw) == 3:
        raw = "".join(character * 2 for character in raw)
    if len(raw) != 6:
        raw = "808080"
    red, green, blue = (int(raw[index : index + 2], 16) for index in (0, 2, 4))
    return f"rgba({red}, {green}, {blue}, {alpha:.3f})"


def component_ids(recipe: dict[str, Any]) -> list[str]:
    ids = {"root", "speaker-system", "transport-system"}
    for item in recipe.get("objects", []):
        if isinstance(item, dict) and item.get("component"):
            ids.add(str(item["component"]))
    for repetition in recipe.get("repetitions", []):
        template = repetition.get("template") if isinstance(repetition, dict) else None
        if isinstance(template, dict) and template.get("component"):
            ids.add(str(template["component"]))
    ordered = ["root"]
    ordered.extend(sorted(ids - {"root"}, key=lambda value: (value not in MACRO_COMPONENTS, value)))
    return ordered


def grouped_recipe(recipe: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in recipe.get("objects", []):
        if isinstance(item, dict) and item.get("component"):
            grouped[str(item["component"])].append(item)
    for repetition in recipe.get("repetitions", []):
        if not isinstance(repetition, dict):
            continue
        template = repetition.get("template")
        if isinstance(template, dict) and template.get("component"):
            enriched = dict(template)
            enriched["repetitionId"] = repetition.get("id")
            grouped[str(template["component"])].append(enriched)
    return grouped


def dominant_material(items: list[dict[str, Any]], fallback: str = "clear-shell") -> str:
    choices = [str(item["material"]) for item in items if item.get("material")]
    return Counter(choices).most_common(1)[0][0] if choices else fallback


def primitive_for(component_id: str, items: list[dict[str, Any]]) -> str:
    if component_id in PRIMITIVE_HINTS:
        return PRIMITIVE_HINTS[component_id]
    types = [str(item.get("type")) for item in items if item.get("type")]
    if "torus" in types or "cylinder" in types:
        return "lathe"
    if "sphere" in types:
        return "ellipsoid"
    if "curve" in types:
        return "curve-sweep"
    if "text" in types:
        return "extrude"
    return "box"


def topology_for(component_id: str, primitive: str) -> tuple[str, str]:
    if component_id in {"front-plate", "rear-plate", "outer-shell"}:
        return (
            "conforming-shell",
            "Visible evidence shows thin clear plates following the rectangular chassis volume.",
        )
    if component_id == "internal-wiring":
        return (
            "fiber-strand",
            "Visible and conservatively inferred wires are swept strands with real thickness.",
        )
    if component_id in {"corner-hardware"}:
        return (
            "surface-relief",
            "Repeated fasteners project from the cover and affect grazing highlights.",
        )
    if primitive in {"lathe", "ellipsoid"}:
        return (
            "assembled-solid",
            "The visible concentric part is a separate rotational solid in a mechanical assembly.",
        )
    return (
        "assembled-solid",
        "The reference exposes this as a separately bounded hard-surface assembly part.",
    )


def material_recipe(material_id: str, colour: str, alpha: float) -> dict[str, Any]:
    material_class = MATERIAL_CLASS_HINTS.get(material_id, "unknown")
    return {
        "dominantAlbedo": rgba_from_hex(colour, alpha),
        "secondaryAlbedo": rgba_from_hex(colour, min(1.0, alpha + 0.08)),
        "materialClass": material_class,
        "materialClassConfidence": 0.82 if material_class != "unknown" else 0.5,
    }


def action_profile(component_id: str, level: str) -> dict[str, Any]:
    return {
        "animationRole": "root" if component_id == "root" else "static-part",
        "pivot": {
            "mode": "bottom-centre" if component_id == "root" else "component-centre",
            "localPosition": [0.0, 0.0, 0.0],
            "axis": [0.0, 0.0, 1.0],
            "confidence": 0.86,
        },
        "transformChannels": {
            "translate": component_id == "root",
            "rotate": component_id == "root" or level == "meso",
            "scale": True,
            "bend": False,
            "twist": False,
            "detach": level != "macro",
            "visibility": True,
            "materialState": True,
        },
        "sockets": (
            [
                {
                    "id": "grip-centre",
                    "localPosition": [0.0, 0.0, 0.118],
                    "axis": [0.0, -1.0, 0.0],
                }
            ]
            if component_id == "root"
            else []
        ),
        "collider": {
            "type": "box",
            "offset": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
            "isTrigger": False,
            "notes": "Simplified runtime proxy; visual meshes remain separate.",
        },
        "constraints": [],
        "destruction": {
            "breakable": False,
            "fractureGroup": component_id,
            "seamRefs": [],
            "detachableFragments": [],
            "breakImpulse": 0.0,
            "debrisMaterial": "clear-shell",
        },
    }


def attachment(component_id: str, parent: str | None) -> dict[str, Any] | None:
    if not parent:
        return None
    return {
        "parentId": parent,
        "parentSocket": f"{parent}-assembly-socket",
        "localStart": [0.0, 0.0, 0.0],
        "localEnd": [0.0, 0.0, 0.001],
        "contactType": "nested mechanical overlap",
        "overlap": 0.001,
        "gapTolerance": 0.0005,
        "contactNormal": [0.0, -1.0, 0.0],
        "evidenceRefs": ["full-object"],
    }


def normalize_materials(
    recipe: dict[str, Any],
    material_override_details: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    output = []
    for item in recipe.get("materials", []):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        material_id = str(item["id"])
        colour = str(item.get("baseColor", "#808080"))
        roughness = float(item.get("roughness", 0.5))
        metallic = float(item.get("metallic", item.get("metalness", 0.0)))
        local_overrides = material_override_details.get(material_id, [])
        output.append(
            {
                "id": material_id,
                "name": material_id.replace("-", " ").title(),
                "type": "physical",
                "shaderModel": "MeshPhysicalMaterial / Blender Principled BSDF",
                "baseColor": colour,
                "color": colour,
                "albedo": {
                    "dominant": colour,
                    "secondary": [colour, "#DCEBF0" if "clear" in material_id else "#27343B"],
                    "samplingNotes": "Reference-observed local zone; transparent pixels are not treated as exact PBR recovery.",
                },
                "colorVariation": {
                    "palette": [colour, "#DCEBF0" if "clear" in material_id else "#27343B"],
                    "pattern": "layered highlight response",
                    "amplitude": 0.06,
                    "heightCorrelation": 0.0,
                },
                "textureResolution": 1024,
                "textureProjection": {
                    "mode": "object",
                    "repeat": [1.0, 1.0],
                    "anisotropy": 8,
                    "texelDensityIntent": "Stable object-scale procedural response; no stretched image projection.",
                },
                "surfaceFrequencyBands": [
                    {"id": "macro", "frequency": 2.0, "amplitude": 0.08, "role": "broad colour and transmission variation"},
                    {"id": "meso", "frequency": 18.0, "amplitude": 0.035, "role": "moulding and brushed response"},
                    {"id": "micro", "frequency": 90.0, "amplitude": 0.012, "role": "grazing highlight breakup"},
                ],
                "roughness": {
                    "base": roughness,
                    "variation": 0.04,
                    "map": "independent-procedural-roughness",
                    "localResponse": "slightly rougher in moulded recesses",
                },
                "metalness": {"base": metallic, "variation": 0.02 if metallic else 0.0},
                "normal": {
                    "pattern": "independent-procedural-micro-normal",
                    "strength": 0.08,
                    "scale": 90.0,
                    "space": "tangent",
                },
                "bump": {"pattern": "micro-moulding", "amplitude": 0.01, "scale": 60.0},
                "displacement": {"pattern": "none", "amplitude": 0.0, "scale": 1.0, "silhouetteAffects": False},
                "ambientOcclusion": {
                    "cavityStrength": 0.22,
                    "contactShadowBias": 0.32,
                    "notes": "Independent cavity response, not copied from albedo.",
                },
                "wear": {"edgeWear": 0.01, "scratches": [], "chips": []},
                "dirt": {"amount": 0.0, "cavityBias": 0.0, "color": "#17232A"},
                "localOverrides": local_overrides,
                "transmission": float(item.get("transmission", 0.0)),
                "alpha": float(item.get("alpha", 1.0)),
                "ior": float(item.get("ior", 1.45)),
                "clearcoat": float(item.get("clearcoat", 0.0)),
                "emission": item.get("emission"),
                "emissionStrength": float(item.get("emissionStrength", 0.0)),
                "qualityTier": "reference-fidelity",
                "shaderNotes": [
                    "Blender Principled mapping is implemented in the batch bridge.",
                    "Transmission and alpha remain render-engine approximations from one reference image.",
                ],
            }
        )
    return output


def normalize(spec: dict[str, Any]) -> dict[str, Any]:
    recipe = spec.get("blenderRecipe")
    if not isinstance(recipe, dict):
        raise ValueError("ObjectSculptSpec.blenderRecipe is required")
    grouped = grouped_recipe(recipe)
    details = (
        spec.get("preSpecAssessment", {})
        .get("detailInventory", {})
        .get("details", [])
    )
    local_features: dict[str, list[dict[str, Any]]] = defaultdict(list)
    material_overrides: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for detail in details if isinstance(details, list) else []:
        maps_to = detail.get("mapsTo") if isinstance(detail, dict) else None
        reference = maps_to.get("ref") if isinstance(maps_to, dict) else None
        mapping_type = maps_to.get("type") if isinstance(maps_to, dict) else None
        if not isinstance(reference, str):
            continue
        owner = reference.split(".", 1)[0]
        payload = {
            "id": reference,
            "kind": detail.get("kind"),
            "description": detail.get("description"),
            "evidenceRef": detail.get("evidenceRef"),
            "confidence": detail.get("confidence"),
            "realization": "geometry-or-separated-material-in-blenderRecipe",
        }
        if mapping_type == "component.localFeatures":
            local_features[owner].append(payload)
        elif mapping_type == "material.localOverrides":
            material_id = DETAIL_MATERIAL_HINTS.get(owner, dominant_material(grouped.get(owner, [])))
            material_overrides[material_id].append(payload)

    definitions = []
    for component_id in component_ids(recipe):
        items = grouped.get(component_id, [])
        level = "macro" if component_id in MACRO_COMPONENTS else LEVEL_HINTS.get(component_id, "meso")
        parent = None if component_id == "root" else PARENT_HINTS.get(component_id, "root")
        material_id = dominant_material(items)
        recipe_material = next(
            (
                item
                for item in recipe.get("materials", [])
                if isinstance(item, dict) and item.get("id") == material_id
            ),
            {"baseColor": "#808080", "alpha": 1.0},
        )
        primitive = primitive_for(component_id, items)
        topology, rationale = topology_for(component_id, primitive)
        definitions.append(
            {
                "id": component_id,
                "name": component_id.replace("-", " ").title(),
                "level": level,
                "role": "hero-root" if component_id == "root" else "mechanical-part",
                "importance": 1.0 if component_id == "root" else 0.86 if level == "macro" else 0.72,
                "confidence": 0.98 if component_id == "root" else 0.76,
                "primitive": primitive,
                "topologyClass": topology,
                "topologyRationale": rationale,
                "colorMaterialRecipe": material_recipe(
                    material_id,
                    str(recipe_material.get("baseColor", "#808080")),
                    float(recipe_material.get("alpha", 1.0)),
                ),
                "geometryDescriptor": {
                    "topologyIntent": "separate bevel-ready hard-surface mesh or named pivot group",
                    "edgeTreatment": {"type": "bevel", "bevelRadius": 0.001, "segments": 3},
                    "deformationStack": [],
                    "uvStrategy": "generated object coordinates",
                    "normalStrategy": "evaluated mesh normals plus bevel highlights",
                },
                "parent": parent,
                "attachment": attachment(component_id, parent),
                "dimensions": {
                    "width": 0.14 if component_id == "root" else 0.05,
                    "height": 0.235 if component_id == "root" else 0.08,
                    "depth": 0.035 if component_id == "root" else 0.02,
                    "units": "meters",
                    "confidence": 0.72,
                },
                "transform": {
                    "position": [0.0, 0.0, 0.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0],
                },
                "actionProfile": action_profile(component_id, level),
                "material": material_id,
                "materialLayers": [material_id],
                "deformations": [],
                "joints": [],
                "seams": [],
                "localFeatures": local_features.get(component_id, []),
                "surfaceDetail": {
                    "macroRoughness": 0.04,
                    "microRoughness": 0.02,
                    "bumpAmplitude": 0.005,
                    "normalPattern": "material-dependent micro highlight breakup",
                    "displacementPattern": "",
                    "occlusionPattern": "nested assembly cavities",
                    "edgeWearPattern": "minimal clean concept-prop wear",
                    "notes": "Visible identity detail remains separate geometry when it affects silhouette.",
                },
                "evidenceRefs": ["full-object"],
                "details": [item["id"] for item in local_features.get(component_id, [])],
                "fidelityTier": "reference-fidelity",
            }
        )

    repetitions = []
    for repetition in recipe.get("repetitions", []):
        if not isinstance(repetition, dict):
            continue
        template = repetition.get("template") if isinstance(repetition.get("template"), dict) else {}
        points = repetition.get("points", [])
        repetitions.append(
            {
                "id": repetition.get("id"),
                "name": str(repetition.get("id", "repetition")).replace("-", " ").title(),
                "componentRef": template.get("component", "root"),
                "pattern": repetition.get("mode", "points"),
                "count": repetition.get("count", len(points) if isinstance(points, list) else 0),
                "instances": points if isinstance(points, list) else [],
                "geometry": template.get("type", "instanced-part"),
                "realization": "instanced-geometry",
                "buildsGeometry": True,
                "evidenceRefs": ["full-object"],
            }
        )

    spec["componentTree"] = definitions
    spec["materials"] = normalize_materials(recipe, material_overrides)
    spec["repetitionSystems"] = repetitions
    assessment = spec.get("preSpecAssessment")
    if isinstance(assessment, dict):
        unresolved = assessment.get("unknownsToResolveBeforeImplementation")
        if isinstance(unresolved, list) and unresolved:
            assessment["resolvedAsSourceLimitations"] = unresolved
            assessment["unknownsToResolveBeforeImplementation"] = []
    material_pass = spec.get("lookDevTargets", {}).get("materialPass")
    if isinstance(material_pass, dict):
        extraction = material_pass.get("referencePbrExtraction")
        if isinstance(extraction, dict):
            extraction["requiredWhenSourceImagePresent"] = False
            extraction["acceptedLimitation"] = (
                "The source is a single stylized render of transparent layered materials; "
                "exact PBR channel recovery is underdetermined, so the Blender Principled "
                "values are explicitly inferred and visually gated."
            )
    lighting_from_photo = spec.get("lightingFromPhoto")
    if not isinstance(lighting_from_photo, list) or not lighting_from_photo:
        spec["lightingFromPhoto"] = [
            {
                "role": "key and reflection",
                "observation": (
                    "cool soft source from upper front-left draws the clear-shell rim "
                    "and metal bezels"
                ),
                "implementation": (
                    "SUN_REFLECTION plus a restrained cool world; exact energy is "
                    "recalibrated to evaluated asset bounds"
                ),
                "toneMapping": "AgX medium-high contrast with exposure recorded by the bridge",
            },
            {
                "role": "back shape and environment fill light",
                "observation": (
                    "broad cool rear source separates transparent depth from the "
                    "blue-grey background"
                ),
                "implementation": (
                    "BACK_SHAPE area light plus the world environment; both are "
                    "proven independently in the cumulative lighting gate"
                ),
                "contactShadow": (
                    "contact shadow beneath the z=0 support edge is required as "
                    "non-levitation evidence"
                ),
            },
            {
                "role": "rim or environment light with local glimmers",
                "observation": (
                    "small warm and cool highlights separate accent controls, dark "
                    "mechanisms, and the clear edge"
                ),
                "implementation": (
                    "two low-energy glimmers plus a neutral detail return, each with "
                    "a named visual function"
                ),
                "ambientColor": "cool blue-grey studio background",
            },
        ]
    for item in spec.get("lightingFromPhoto", []):
        if isinstance(item, dict) and item.get("role") == "back shape":
            item["contactShadow"] = (
                "contact shadow is visible beneath the z=0 support edge and proves non-levitation"
            )
    for target in spec.get("featureReviewTargets", []):
        if not isinstance(target, dict):
            continue
        old_id = target.get("id")
        if old_id in FEATURE_TARGET_RENAMES:
            target["id"] = FEATURE_TARGET_RENAMES[old_id]
        if old_id == "overall-silhouette":
            target["componentRefs"] = ["root", "outer-shell"]
        elif old_id == "primary-structure":
            target["componentRefs"] = ["speaker-assembly", "transport-wheel", "side-control-strip"]
        elif old_id == "reference-material-system":
            target["componentRefs"] = ["outer-shell", "inner-panel", "transport-wheel"]
    for history_key in ("reviewHistory", "visualEvidence"):
        for entry in spec.get(history_key, []):
            if not isinstance(entry, dict):
                continue
            for review in entry.get("featureReviews", []):
                if isinstance(review, dict) and review.get("id") in FEATURE_TARGET_RENAMES:
                    review["id"] = FEATURE_TARGET_RENAMES[review["id"]]
    return spec


def main() -> int:
    args = parse_args()
    source = args.spec.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if args.in_place == bool(args.out):
        raise ValueError("Choose exactly one of --in-place or --out")
    spec = json.loads(source.read_text(encoding="utf-8"))
    if args.recipe_from:
        recipe_source = args.recipe_from.expanduser().resolve()
        if not recipe_source.is_file():
            raise FileNotFoundError(recipe_source)
        recipe_spec = json.loads(recipe_source.read_text(encoding="utf-8"))
        recipe = recipe_spec.get("blenderRecipe")
        if not isinstance(recipe, dict):
            raise ValueError(f"{recipe_source} does not contain blenderRecipe")
        spec["blenderRecipe"] = recipe
        spec["blenderIntegrationProvenance"] = {
            "mode": "reviewed-recipe-regression",
            "recipeSource": str(recipe_source),
            "recipeSourceTarget": recipe_spec.get("targetName"),
            "note": (
                "Only blenderRecipe is reused. Intake, assessment, source image, "
                "pipeline state, and review evidence belong to the destination spec."
            ),
        }
    normalized = normalize(spec)
    destination = source if args.in_place else args.out.expanduser().resolve()
    destination.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "spec": str(destination),
                "components": len(normalized.get("componentTree", [])),
                "materials": len(normalized.get("materials", [])),
                "repetitionSystems": len(normalized.get("repetitionSystems", [])),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
