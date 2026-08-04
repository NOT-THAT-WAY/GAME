using UnityEditor;
using UnityEngine;

namespace NotThatWay.Game.Editor
{
    [InitializeOnLoad]
    internal static class TeamProjectSettings
    {
        private const string ExpectedUnityVersion = "6000.3.20f1";

        static TeamProjectSettings()
        {
            EditorApplication.delayCall += ApplyRequiredSettings;
        }

        [MenuItem("GAME/Validate Project Setup")]
        private static void ValidateProjectSetup()
        {
            ApplyRequiredSettings();

            if (Application.unityVersion != ExpectedUnityVersion)
            {
                Debug.LogError($"GAME expects Unity {ExpectedUnityVersion}, but this Editor is {Application.unityVersion}.");
                return;
            }

            Debug.Log("GAME project setup is valid: exact Unity version, Force Text and Visible Meta Files.");
        }

        private static void ApplyRequiredSettings()
        {
            var changed = false;

            if (EditorSettings.serializationMode != SerializationMode.ForceText)
            {
                EditorSettings.serializationMode = SerializationMode.ForceText;
                changed = true;
            }

            if (EditorSettings.externalVersionControl != "Visible Meta Files")
            {
                EditorSettings.externalVersionControl = "Visible Meta Files";
                changed = true;
            }

            if (changed)
            {
                AssetDatabase.SaveAssets();
                Debug.Log("GAME applied shared serialization and version-control settings.");
            }

            if (Application.unityVersion != ExpectedUnityVersion)
            {
                Debug.LogError($"Wrong Unity version. Expected {ExpectedUnityVersion}; running {Application.unityVersion}.");
            }
        }
    }
}
