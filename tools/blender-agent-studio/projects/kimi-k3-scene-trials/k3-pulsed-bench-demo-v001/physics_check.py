"""Preuves physiques v2 pour k3-pulsed-bench-demo-v001.

Conforme a knowledge/SCENE_TRIAL_EVALUATION_RULES.md :
  - mesure la GEOMETRIE EVALUEE (modifiers, parenting, transforms appliques) ;
  - un seul repere declare : le monde de scene/trial.blend, en metres ;
  - la matrice du parent anime est recalculee a CHAQUE frame ;
  - echantillonnage = toutes les frames (sample_frame_step = 1) ;
  - distance signee AU PLAN DERIVE DU MESH du banc + recouvrement BVH ;
  - rapporte la pire valeur, sa frame et le nombre de frames hors seuil.

  blender -b scene/trial.blend --python physics_check.py
"""

import json
import os

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

TRIAL_DIR = os.path.dirname(os.path.abspath(__file__))
TRIAL_ID = "k3-pulsed-bench-demo-v001"
OUT = os.path.join(TRIAL_DIR, "diagnostics", "physical-validation.json")
CSV = os.path.join(TRIAL_DIR, "diagnostics", "physics-timeline.csv")

BENCH = "K3_PULSED_BENCH_V001_BENCH"
CAM = "K3_PULSED_BENCH_V001_CAMERA"
SHELLS = ("PV2_shell_back", "PV2_shell_front")

THRESHOLDS = {
    "environment_penetration": ("<=", 0.002),
    "support_gap": ("<=", 0.005),
    "planted_contact_drift": ("<=", 0.005),
    "swing_clearance": (">=", 0.010),
    "camera_clearance": (">=", 0.080),
}


def evaluated_verts(obj, deps):
    """Sommets monde de la geometrie EVALUEE, en numpy."""
    ev = obj.evaluated_get(deps)
    me = ev.to_mesh()
    if me is None or len(me.vertices) == 0:
        if me is not None:
            ev.to_mesh_clear()
        return None
    n = len(me.vertices)
    flat = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get("co", flat)
    co = flat.reshape(n, 3)
    m = np.array(ev.matrix_world.transposed())          # (4,4) pour co @ M
    world = np.column_stack([co, np.ones(n)]) @ m
    ev.to_mesh_clear()
    return world[:, :3]


def evaluated_bvh(obj, deps):
    ev = obj.evaluated_get(deps)
    me = ev.to_mesh()
    if me is None:
        return None
    mw = ev.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    me.calc_loop_triangles()
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    ev.to_mesh_clear()
    if not tris:
        return None
    return BVHTree.FromPolygons(verts, tris, all_triangles=True)


def subject_objects():
    return [o for o in bpy.data.objects
            if o.type == "MESH" and o.name.startswith("PV2_")
            and not o.hide_render and not o.hide_viewport]


def main():
    scene = bpy.context.scene
    f0, f1 = scene.frame_start, scene.frame_end
    bench = bpy.data.objects[BENCH]
    cam = bpy.data.objects[CAM]
    shells = [bpy.data.objects[n] for n in SHELLS if n in bpy.data.objects]

    rows = []
    worst = {k: None for k in THRESHOLDS}
    outside = {k: 0 for k in THRESHOLDS}
    ref_xy = None

    for frame in range(f0, f1 + 1):
        scene.frame_set(frame)
        # depsgraph relu a chaque frame : la matrice du root anime doit suivre
        deps = bpy.context.evaluated_depsgraph_get()

        # Plan d'appui DERIVE DU MESH du banc, jamais code en dur.
        bench_v = evaluated_verts(bench, deps)
        bench_top = float(bench_v[:, 2].max())

        subj = subject_objects()
        pts = [p for p in (evaluated_verts(o, deps) for o in subj) if p is not None]
        allp = np.concatenate(pts, axis=0)
        min_z = float(allp[:, 2].min())

        support_gap = max(0.0, min_z - bench_top)
        penetration = max(0.0, bench_top - min_z)

        # Recouvrement BVH coque/banc : un solide peut traverser sans que le
        # minimum vertical le montre.
        bench_bvh = evaluated_bvh(bench, deps)
        overlap_pairs = 0
        for sh in shells:
            sh_bvh = evaluated_bvh(sh, deps)
            if sh_bvh and bench_bvh:
                overlap_pairs += len(sh_bvh.overlap(bench_bvh))

        # Drift tangentiel de l'appui : barycentre XY des sommets au contact.
        contact = allp[allp[:, 2] <= bench_top + 0.0015]
        cxy = contact[:, :2].mean(axis=0) if len(contact) else allp[:, :2].mean(axis=0)
        if ref_xy is None:
            ref_xy = cxy
        drift = float(np.hypot(*(cxy - ref_xy)))

        # Clearance camera : nearest-surface sur le decor + le sujet.
        cam_pos = cam.matrix_world.translation
        near = []
        for o in shells + [bench]:
            b = evaluated_bvh(o, deps)
            if b:
                loc, _, _, _ = b.find_nearest(cam_pos)
                if loc is not None:
                    near.append((cam_pos - loc).length)
        cam_clear = float(min(near)) if near else 0.0

        values = {
            "environment_penetration": penetration,
            "support_gap": support_gap,
            "planted_contact_drift": drift,
            "camera_clearance": cam_clear,
        }
        for name, val in values.items():
            op, thr = THRESHOLDS[name]
            bad = val > thr if op == "<=" else val < thr
            if bad:
                outside[name] += 1
            cur = worst[name]
            if cur is None or (op == "<=" and val > cur[0]) or (op == ">=" and val < cur[0]):
                worst[name] = (val, frame)
        rows.append((frame, penetration, support_gap, drift, cam_clear, overlap_pairs))

    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    with open(CSV, "w") as fh:
        fh.write("frame,penetration_m,support_gap_m,drift_m,camera_clearance_m,bvh_overlap_pairs\n")
        for r in rows:
            fh.write(f"{r[0]},{r[1]:.6f},{r[2]:.6f},{r[3]:.6f},{r[4]:.6f},{r[5]}\n")

    total_overlap = sum(r[5] for r in rows)

    def check(name, applicable=True, reason=None):
        op, thr = THRESHOLDS[name]
        if not applicable:
            return {"applicable": False, "not_applicable_reason": reason}
        val, frame = worst[name]
        passed = val <= thr if op == "<=" else val >= thr
        return {
            "applicable": True,
            "operator": op,
            "value_m": round(val, 6),
            "threshold_m": thr,
            "passed": bool(passed),
            "worst_frame": int(frame),
            "frames_outside_threshold": int(outside[name]),
            "evidence": ["diagnostics/physics-timeline.csv",
                         "gates/proof-support.png",
                         "gates/proof-side.png"],
        }

    checks = {
        "environment_penetration": check("environment_penetration"),
        "support_gap": check("support_gap"),
        "planted_contact_drift": check("planted_contact_drift"),
        "camera_clearance": check("camera_clearance"),
        "swing_clearance": check(
            "swing_clearance", applicable=False,
            reason=("Aucun membre en swing. Les seules pieces mobiles sont des "
                    "commandes guidees dans leur logement (molette revolute, "
                    "sliders prismatiques, D-pad bascule) : elles sont EN CONTACT "
                    "avec la coque par construction, un seuil de degagement de "
                    "10 mm n'a pas de sens pour elles. Leurs limites sont "
                    "verifiees par le contrat d'objet pulsed.json.")),
    }

    applicable = [c for c in checks.values() if c.get("applicable")]
    passed = all(c["passed"] for c in applicable) and total_overlap == 0

    critical = []
    if not passed:
        if checks["environment_penetration"]["applicable"] and not checks["environment_penetration"]["passed"]:
            critical.append("collision_or_environment_traversal")
        if total_overlap > 0 and "collision_or_environment_traversal" not in critical:
            critical.append("collision_or_environment_traversal")
        if checks["support_gap"]["applicable"] and not checks["support_gap"]["passed"]:
            critical.append("levitation_or_missing_required_support")
        if checks["planted_contact_drift"]["applicable"] and not checks["planted_contact_drift"]["passed"]:
            critical.append("unmotivated_drift_or_contact_slip")

    doc = {
        "schema_version": 2,
        "trial_id": TRIAL_ID,
        "status": "completed",
        "method": {
            "evaluated_geometry": True,
            "modifiers_and_armature_applied_in_evaluation": True,
            "coordinate_space": "monde de scene/trial.blend, en metres",
            "coordinate_space_source": (
                "scene.unit_settings METRIC ; le modele natif est en BU ou "
                "1 BU = 1 cm, ramene a l'echelle reelle par "
                "K3_PULSED_BENCH_V001_ROOT (scale 0.01), donc les coordonnees "
                "monde SONT des metres et se comparent directement aux seuils."),
            "moving_parent_evaluated_each_frame": True,
            "sample_frame_step": 1,
            "frame_start": int(f0),
            "frame_end": int(f1),
            "distance_method": (
                "distance verticale signee de chaque sommet evalue du sujet au "
                "plan d'appui DERIVE DU MESH du banc (max Z de ses sommets "
                "evalues, recalcule a chaque frame), et nearest-surface BVH "
                "pour la clearance camera"),
            "overlap_method": (
                "BVHTree.overlap entre les triangles evalues des demi-coques et "
                "ceux du banc, a chaque frame ; "
                f"paires en intersection sur toute la plage : {total_overlap}"),
        },
        "semantic_pairs": [
            {"pair": "coque arriere de Pulsed / plateau du banc",
             "type": "support_contact",
             "expected": "contact planté permanent, sans penetration ni glissement"},
            {"pair": "corps de Pulsed / plateau du banc",
             "type": "collision",
             "expected": "aucune traversee"},
            {"pair": "camera / sujet et decor",
             "type": "camera_corridor",
             "expected": "aucune approche sous 80 mm sur toute la trajectoire"},
        ],
        "checks": checks,
        "passed": bool(passed),
        "critical_failures": critical,
        "proof_views": ["gates/proof-support.png", "gates/proof-side.png",
                        "gates/proof-hero.png"],
        "limitations": [
            ("Le sujet est pose et immobile : le contact est statique, ce qui "
             "rend les preuves d'appui simples a satisfaire. Ce n'est pas un "
             "test de locomotion."),
            ("Les courses des commandes sont jouees sans main visible. La "
             "convention est declaree dans brief.json et dans le contrat "
             "d'objet ; l'affordance reelle reste 'actionne au pouce'."),
            ("Le recouvrement BVH n'est evalue qu'entre les demi-coques et le "
             "banc : les commandes sont interieures au volume de la coque et ne "
             "peuvent pas atteindre le plateau."),
        ],
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)

    print(f"[physics] passed={passed} overlap_pairs={total_overlap}")
    for name, c in checks.items():
        if c.get("applicable"):
            print(f"  {name:26s} {c['value_m']*1000:8.3f} mm  seuil "
                  f"{c['operator']} {c['threshold_m']*1000:.1f} mm  "
                  f"pire frame {c['worst_frame']}  hors seuil {c['frames_outside_threshold']}")
        else:
            print(f"  {name:26s} non applicable")
    print(f"[ok] -> {OUT}")


if __name__ == "__main__":
    main()
