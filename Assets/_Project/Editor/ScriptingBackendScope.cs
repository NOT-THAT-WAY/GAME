using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;

namespace NotThatWay.Game.Editor
{
    /// <summary>
    /// Applies a build-only scripting backend and always restores the project
    /// backend, including when BuildPipeline throws or returns a failed report.
    /// </summary>
    internal sealed class ScriptingBackendScope : IDisposable
    {
        private const string ProjectSettingsRelativePath =
            "ProjectSettings/ProjectSettings.asset";

        private readonly NamedBuildTarget _target;
        private readonly ScriptingImplementation _previousBackend;
        private readonly bool _restoreRequired;
        private readonly string _projectSettingsPath;
        private readonly byte[] _projectSettingsSnapshot;

        internal ScriptingBackendScope(
            BuildTarget buildTarget,
            ScriptingImplementation? forcedBackend)
        {
            _target = NamedBuildTarget.FromBuildTargetGroup(
                BuildPipeline.GetBuildTargetGroup(buildTarget));
            _previousBackend = PlayerSettings.GetScriptingBackend(_target);

            Debug.Log(
                $"[GAME-BUILD-BACKEND] target={buildTarget} previous={_previousBackend} " +
                $"forced={(forcedBackend.HasValue ? forcedBackend.Value.ToString() : "none")}");

            if (!forcedBackend.HasValue || forcedBackend.Value == _previousBackend)
                return;

            // Unity may flush the forced backend after this scope unwinds even
            // though GetScriptingBackend already reports the restored value.
            // Keep the exact serialized file so a failed build cannot dirty the
            // repository during the editor's delayed ProjectSettings write.
            var projectRoot = Directory.GetParent(Application.dataPath) ??
                throw new InvalidOperationException("Racine du projet Unity introuvable.");
            _projectSettingsPath = Path.Combine(
                projectRoot.FullName,
                ProjectSettingsRelativePath);
            _projectSettingsSnapshot = File.ReadAllBytes(_projectSettingsPath);

            PlayerSettings.SetScriptingBackend(_target, forcedBackend.Value);
            _restoreRequired = true;
            Debug.Log(
                $"[GAME-BUILD-BACKEND] applied={PlayerSettings.GetScriptingBackend(_target)}");
        }

        public void Dispose()
        {
            if (_restoreRequired)
            {
                PlayerSettings.SetScriptingBackend(_target, _previousBackend);
                File.WriteAllBytes(_projectSettingsPath, _projectSettingsSnapshot);
                // Reload the restored bytes before Unity's shutdown save pass.
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                Debug.Log(
                    $"[GAME-BUILD-BACKEND] restored={PlayerSettings.GetScriptingBackend(_target)}");
            }
        }
    }
}
