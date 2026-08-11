using System;
using UnityEditor;
using UnityEditor.Build;

namespace NotThatWay.Game.Editor
{
    /// <summary>
    /// Applies a build-only scripting backend and always restores the project
    /// backend, including when BuildPipeline throws or returns a failed report.
    /// </summary>
    internal sealed class ScriptingBackendScope : IDisposable
    {
        private readonly NamedBuildTarget _target;
        private readonly ScriptingImplementation _previousBackend;
        private readonly bool _restoreRequired;

        internal ScriptingBackendScope(
            BuildTarget buildTarget,
            ScriptingImplementation? forcedBackend)
        {
            _target = NamedBuildTarget.FromBuildTargetGroup(
                BuildPipeline.GetBuildTargetGroup(buildTarget));
            _previousBackend = PlayerSettings.GetScriptingBackend(_target);

            if (!forcedBackend.HasValue || forcedBackend.Value == _previousBackend)
                return;

            PlayerSettings.SetScriptingBackend(_target, forcedBackend.Value);
            _restoreRequired = true;
        }

        public void Dispose()
        {
            if (_restoreRequired)
                PlayerSettings.SetScriptingBackend(_target, _previousBackend);
        }
    }
}
