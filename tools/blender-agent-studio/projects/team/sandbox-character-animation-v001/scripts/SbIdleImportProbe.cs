// TEMPORARY import probe for the SB_Idle candidate FBX.
//
// Lives in Assets/_GeneratedLocal/ (gitignored) and is deleted after the run.
// It reads and reports only; it does not touch Assets/_Project/Player/, the
// Animator Controller, any Animator parameter, or any gameplay script.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

public static class SbIdleImportProbe
{
    const string AssetPath = "Assets/_GeneratedLocal/SandboxAnimTemp/SB_Idle_candidate_TEMP.fbx";
    const string OutPath = "Assets/_GeneratedLocal/SandboxAnimTemp/unity-import-probe.json";

    static readonly string[] ExpectedBones =
    {
        "BAS_PUNCH_root", "BAS_PUNCH_body",
        "BAS_PUNCH_upperarm.L", "BAS_PUNCH_forearm.L", "BAS_PUNCH_hand.L",
        "BAS_PUNCH_upperarm.R", "BAS_PUNCH_forearm.R", "BAS_PUNCH_hand.R",
        "BAS_PUNCH_foot.L", "BAS_PUNCH_foot.R"
    };

    static string J(string s) => "\"" + (s ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
    static string F(float v) => v.ToString("R", CultureInfo.InvariantCulture);
    static string F(double v) => v.ToString("R", CultureInfo.InvariantCulture);
    static string B(bool v) => v ? "true" : "false";

    public static void Run()
    {
        var sb = new StringBuilder();
        var notes = new List<string>();
        bool ok = true;

        AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);

        var imp = AssetImporter.GetAtPath(AssetPath) as ModelImporter;
        if (imp == null)
        {
            File.WriteAllText(OutPath, "{\"error\":\"ModelImporter not found at " + AssetPath + "\"}");
            EditorApplication.Exit(2);
            return;
        }

        // ---- apply the contract's import settings ----
        imp.animationType = ModelImporterAnimationType.Generic;   // Generic rig
        imp.importAnimation = true;
        imp.useFileScale = true;
        imp.globalScale = 1f;
        imp.importCameras = false;
        imp.importLights = false;
        imp.optimizeGameObjects = false;
        imp.importConstraints = false;
        imp.animationCompression = ModelImporterAnimationCompression.Off;

        // The loop flag is a Unity IMPORTER setting (.meta), not data inside the
        // FBX. Declare the clip explicitly so loopTime can be turned on.
        var defaults = imp.defaultClipAnimations;
        if (defaults != null && defaults.Length > 0)
        {
            for (int i = 0; i < defaults.Length; i++)
            {
                defaults[i].loopTime = true;
                defaults[i].loopPose = false;
                defaults[i].lockRootRotation = false;
            }
            imp.clipAnimations = defaults;
        }
        imp.SaveAndReimport();
        AssetDatabase.Refresh();

        // ---- read back ----
        var all = AssetDatabase.LoadAllAssetsAtPath(AssetPath);
        var go = AssetDatabase.LoadAssetAtPath<GameObject>(AssetPath);
        var clips = all.OfType<AnimationClip>()
                       .Where(c => !c.name.StartsWith("__preview__"))
                       .ToArray();

        sb.Append("{\n");
        sb.Append("  \"unity_version\": ").Append(J(Application.unityVersion)).Append(",\n");
        sb.Append("  \"asset_path\": ").Append(J(AssetPath)).Append(",\n");

        // ---- importer ----
        sb.Append("  \"importer\": {\n");
        sb.Append("    \"animationType\": ").Append(J(imp.animationType.ToString())).Append(",\n");
        sb.Append("    \"is_generic\": ").Append(B(imp.animationType == ModelImporterAnimationType.Generic)).Append(",\n");
        sb.Append("    \"importAnimation\": ").Append(B(imp.importAnimation)).Append(",\n");
        sb.Append("    \"useFileScale\": ").Append(B(imp.useFileScale)).Append(",\n");
        sb.Append("    \"globalScale\": ").Append(F(imp.globalScale)).Append(",\n");
        sb.Append("    \"rootMotionBoneName\": ").Append(J(imp.motionNodeName)).Append(",\n");
        sb.Append("    \"importCameras\": ").Append(B(imp.importCameras)).Append(",\n");
        sb.Append("    \"importLights\": ").Append(B(imp.importLights)).Append("\n");
        sb.Append("  },\n");
        if (imp.animationType != ModelImporterAnimationType.Generic) { ok = false; notes.Add("animationType is not Generic"); }

        // ---- clips ----
        sb.Append("  \"clips\": [\n");
        for (int i = 0; i < clips.Length; i++)
        {
            var c = clips[i];
            var s = AnimationUtility.GetAnimationClipSettings(c);
            var bindings = AnimationUtility.GetCurveBindings(c);
            var bonePaths = bindings.Select(b => b.path).Distinct().OrderBy(x => x).ToArray();
            int frames = Mathf.RoundToInt(c.length * c.frameRate) + 1;

            sb.Append("    {\n");
            sb.Append("      \"name\": ").Append(J(c.name)).Append(",\n");
            sb.Append("      \"name_is_exactly_SB_Idle\": ").Append(B(c.name == "SB_Idle")).Append(",\n");
            sb.Append("      \"length_s\": ").Append(F(c.length)).Append(",\n");
            sb.Append("      \"frameRate\": ").Append(F(c.frameRate)).Append(",\n");
            sb.Append("      \"frameRate_is_30\": ").Append(B(Mathf.Abs(c.frameRate - 30f) < 1e-4f)).Append(",\n");
            sb.Append("      \"sampled_frames\": ").Append(frames).Append(",\n");
            sb.Append("      \"sampled_frames_is_60\": ").Append(B(frames == 60)).Append(",\n");
            sb.Append("      \"expected_length_59_over_30_s\": ").Append(F(59f / 30f)).Append(",\n");
            sb.Append("      \"length_matches_expected\": ").Append(B(Mathf.Abs(c.length - 59f / 30f) < 1e-3f)).Append(",\n");
            sb.Append("      \"isLooping\": ").Append(B(c.isLooping)).Append(",\n");
            sb.Append("      \"loopTime\": ").Append(B(s.loopTime)).Append(",\n");
            sb.Append("      \"loopBlend\": ").Append(B(s.loopBlend)).Append(",\n");
            sb.Append("      \"cycleOffset\": ").Append(F(s.cycleOffset)).Append(",\n");
            sb.Append("      \"hasRootCurves\": ").Append(B(c.hasRootCurves)).Append(",\n");
            sb.Append("      \"hasMotionCurves\": ").Append(B(c.hasMotionCurves)).Append(",\n");
            sb.Append("      \"hasGenericRootTransform\": ").Append(B(c.hasGenericRootTransform)).Append(",\n");
            sb.Append("      \"averageSpeed\": [").Append(F(c.averageSpeed.x)).Append(",").Append(F(c.averageSpeed.y)).Append(",").Append(F(c.averageSpeed.z)).Append("],\n");
            sb.Append("      \"averageSpeed_magnitude\": ").Append(F(c.averageSpeed.magnitude)).Append(",\n");
            sb.Append("      \"apparentSpeed\": ").Append(F(c.apparentSpeed)).Append(",\n");
            sb.Append("      \"curve_binding_count\": ").Append(bindings.Length).Append(",\n");
            sb.Append("      \"animated_transform_paths\": [")
              .Append(string.Join(",", bonePaths.Select(J))).Append("],\n");

            // root motion: the root bone's curves must be perfectly static
            float rootMaxPos = 0f, rootMaxRot = 0f;
            foreach (var bnd in bindings)
            {
                bool isRoot = bnd.path == "BAS_PUNCH_root" || bnd.path.EndsWith("/BAS_PUNCH_root");
                if (!isRoot) continue;
                var curve = AnimationUtility.GetEditorCurve(c, bnd);
                if (curve == null || curve.keys.Length == 0) continue;
                float mn = curve.keys.Min(k => k.value);
                float mx = curve.keys.Max(k => k.value);
                float d = mx - mn;
                if (bnd.propertyName.StartsWith("m_LocalPosition")) rootMaxPos = Mathf.Max(rootMaxPos, d);
                if (bnd.propertyName.StartsWith("m_LocalRotation")) rootMaxRot = Mathf.Max(rootMaxRot, d);
            }
            sb.Append("      \"root_bone_curve_max_position_delta\": ").Append(F(rootMaxPos)).Append(",\n");
            sb.Append("      \"root_bone_curve_max_rotation_delta\": ").Append(F(rootMaxRot)).Append(",\n");
            sb.Append("      \"root_motion_is_zero\": ").Append(B(rootMaxPos < 1e-6f && rootMaxRot < 1e-6f)).Append("\n");
            sb.Append("    }").Append(i < clips.Length - 1 ? "," : "").Append("\n");

            if (c.name != "SB_Idle") { ok = false; notes.Add("clip name is '" + c.name + "', expected SB_Idle"); }
            if (Mathf.Abs(c.frameRate - 30f) > 1e-4f) { ok = false; notes.Add("frameRate is not 30"); }
            if (frames != 60) { ok = false; notes.Add("sampled frames = " + frames + ", expected 60"); }
            if (!s.loopTime) { ok = false; notes.Add("loopTime is false"); }
            if (rootMaxPos > 1e-6f || rootMaxRot > 1e-6f) { ok = false; notes.Add("root bone curves are not static"); }
            if (c.averageSpeed.magnitude > 1e-6f) { notes.Add("averageSpeed is non-zero: " + c.averageSpeed); }
        }
        sb.Append("  ],\n");
        sb.Append("  \"clip_count\": ").Append(clips.Length).Append(",\n");
        if (clips.Length != 1) { ok = false; notes.Add("expected exactly 1 clip, found " + clips.Length); }

        // ---- hierarchy / parasites / budgets ----
        var transforms = go.GetComponentsInChildren<Transform>(true);
        var skinned = go.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        var plainMR = go.GetComponentsInChildren<MeshRenderer>(true);
        var cams = go.GetComponentsInChildren<Camera>(true);
        var lights = go.GetComponentsInChildren<Light>(true);

        int tris = 0, verts = 0, maxBonesPerVertex = 0;
        foreach (var smr in skinned)
        {
            var m = smr.sharedMesh;
            if (m == null) continue;
            verts += m.vertexCount;
            for (int si = 0; si < m.subMeshCount; si++) tris += (int)(m.GetIndexCount(si) / 3);
            var bpv = m.GetBonesPerVertex();
            if (bpv.Length > 0) maxBonesPerVertex = Mathf.Max(maxBonesPerVertex, bpv.Max(x => (int)x));
        }

        var boneNames = skinned.SelectMany(s => s.bones ?? new Transform[0])
                               .Where(t => t != null).Select(t => t.name)
                               .Distinct().OrderBy(x => x).ToArray();
        var missing = ExpectedBones.Where(b => !boneNames.Contains(b)).ToArray();
        var unexpected = boneNames.Where(b => !ExpectedBones.Contains(b)).ToArray();

        sb.Append("  \"hierarchy\": {\n");
        sb.Append("    \"root_name\": ").Append(J(go.name)).Append(",\n");
        sb.Append("    \"root_localScale\": [").Append(F(go.transform.localScale.x)).Append(",")
          .Append(F(go.transform.localScale.y)).Append(",").Append(F(go.transform.localScale.z)).Append("],\n");
        sb.Append("    \"transform_count\": ").Append(transforms.Length).Append(",\n");
        sb.Append("    \"skinned_mesh_renderers\": ").Append(skinned.Length).Append(",\n");
        sb.Append("    \"plain_mesh_renderers\": ").Append(plainMR.Length).Append(",\n");
        sb.Append("    \"cameras\": ").Append(cams.Length).Append(",\n");
        sb.Append("    \"lights\": ").Append(lights.Length).Append(",\n");
        sb.Append("    \"no_parasites\": ").Append(B(cams.Length == 0 && lights.Length == 0 && plainMR.Length == 0)).Append(",\n");
        sb.Append("    \"total_vertices\": ").Append(verts).Append(",\n");
        sb.Append("    \"total_triangles\": ").Append(tris).Append(",\n");
        sb.Append("    \"within_6000_tri_budget\": ").Append(B(tris <= 6000)).Append(",\n");
        sb.Append("    \"bone_count\": ").Append(boneNames.Length).Append(",\n");
        sb.Append("    \"within_16_bone_budget\": ").Append(B(boneNames.Length <= 16)).Append(",\n");
        sb.Append("    \"max_bones_per_vertex\": ").Append(maxBonesPerVertex).Append(",\n");
        sb.Append("    \"within_4_influence_budget\": ").Append(B(maxBonesPerVertex <= 4)).Append(",\n");
        sb.Append("    \"bones\": [").Append(string.Join(",", boneNames.Select(J))).Append("],\n");
        sb.Append("    \"missing_bones\": [").Append(string.Join(",", missing.Select(J))).Append("],\n");
        sb.Append("    \"unexpected_bones\": [").Append(string.Join(",", unexpected.Select(J))).Append("],\n");
        sb.Append("    \"bone_names_match_source\": ").Append(B(missing.Length == 0 && unexpected.Length == 0)).Append("\n");
        sb.Append("  },\n");

        if (cams.Length > 0 || lights.Length > 0 || plainMR.Length > 0) { ok = false; notes.Add("parasite objects present in imported hierarchy"); }
        if (missing.Length > 0 || unexpected.Length > 0) { ok = false; notes.Add("bone set differs from source"); }
        if (tris > 6000) { ok = false; notes.Add("triangle budget exceeded"); }
        if (maxBonesPerVertex > 4) { ok = false; notes.Add("more than 4 influences per vertex"); }

        // ---- orientation & scale, in Unity's frame (Y up, Z forward) ----
        // Measured on an INSTANTIATED model: a SkinnedMeshRenderer's
        // sharedMesh.bounds are in that renderer's own bind space, so combining
        // them across renderers is meaningless. Renderer.bounds is the world AABB
        // and accounts for the whole transform chain and the FBX unit scale.
        //
        // Blender's Z height (1.34 m) must land on Unity Y; the eye patch sat at
        // Blender Y = -0.44, so in Unity it must sit at POSITIVE Z (forward).
        var inst = (GameObject)PrefabUtility.InstantiatePrefab(go);
        inst.transform.position = Vector3.zero;
        inst.transform.rotation = Quaternion.identity;
        var instSkinned = inst.GetComponentsInChildren<SkinnedMeshRenderer>(true);

        Bounds world = new Bounds();
        bool winit = false;
        foreach (var smr in instSkinned)
        {
            if (!winit) { world = smr.bounds; winit = true; }
            else world.Encapsulate(smr.bounds);
        }

        float eyeZ = float.NaN, bodyZ = float.NaN;
        var bodySmr = instSkinned.FirstOrDefault(s => s.name.Contains("Body"));
        if (bodySmr != null && bodySmr.sharedMesh != null)
        {
            var baked = new Mesh();
            bodySmr.BakeMesh(baked, true);
            var vtx = baked.vertices;
            var l2w = bodySmr.transform.localToWorldMatrix;
            var mats = bodySmr.sharedMaterials;
            double allSum = 0;
            for (int vi = 0; vi < vtx.Length; vi++) allSum += l2w.MultiplyPoint3x4(vtx[vi]).z;
            if (vtx.Length > 0) bodyZ = (float)(allSum / vtx.Length);

            for (int si = 0; si < baked.subMeshCount && si < mats.Length; si++)
            {
                if (mats[si] == null || !mats[si].name.Contains("Eye")) continue;
                var uniq = baked.GetTriangles(si).Distinct().ToArray();
                if (uniq.Length == 0) continue;
                double sum = 0;
                foreach (var vi in uniq) sum += l2w.MultiplyPoint3x4(vtx[vi]).z;
                eyeZ = (float)(sum / uniq.Length);
            }
            UnityEngine.Object.DestroyImmediate(baked);
        }

        bool facesForward = !float.IsNaN(eyeZ) && !float.IsNaN(bodyZ) && eyeZ > bodyZ;
        bool heightOk = Mathf.Abs(world.size.y - 1.34f) < 0.03f;

        sb.Append("  \"orientation_and_scale\": {\n");
        sb.Append("    \"measured_on\": ").Append(J("instantiated model, world-space Renderer.bounds")).Append(",\n");
        sb.Append("    \"world_bounds_size\": [").Append(F(world.size.x)).Append(",")
          .Append(F(world.size.y)).Append(",").Append(F(world.size.z)).Append("],\n");
        sb.Append("    \"world_bounds_min_y\": ").Append(F(world.min.y)).Append(",\n");
        sb.Append("    \"height_on_unity_Y_m\": ").Append(F(world.size.y)).Append(",\n");
        sb.Append("    \"expected_height_m\": 1.34,\n");
        sb.Append("    \"height_matches_source\": ").Append(B(heightOk)).Append(",\n");
        sb.Append("    \"blender_size_xyz_for_reference\": [1.759,1.058,1.349],\n");
        sb.Append("    \"eye_patch_center_world_z\": ").Append(float.IsNaN(eyeZ) ? "null" : F(eyeZ)).Append(",\n");
        sb.Append("    \"body_center_world_z\": ").Append(float.IsNaN(bodyZ) ? "null" : F(bodyZ)).Append(",\n");
        sb.Append("    \"faces_positive_z_forward\": ").Append(B(facesForward)).Append("\n");
        sb.Append("  },\n");

        UnityEngine.Object.DestroyImmediate(inst);

        if (!heightOk) { ok = false; notes.Add("height on Unity Y is " + world.size.y + ", expected ~1.34"); }
        if (!facesForward) { ok = false; notes.Add("character does not face +Z (eyeZ=" + eyeZ + ", bodyZ=" + bodyZ + ")"); }

        sb.Append("  \"notes\": [").Append(string.Join(",", notes.Select(J))).Append("],\n");
        sb.Append("  \"passed\": ").Append(B(ok)).Append("\n");
        sb.Append("}\n");

        File.WriteAllText(OutPath, sb.ToString());
        Debug.Log("SB_IDLE_PROBE_DONE passed=" + ok);
        EditorApplication.Exit(0);
    }
}
