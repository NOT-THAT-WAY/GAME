using System;
using System.Collections;
using System.Globalization;
using System.IO;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Capture l'écran du player puis quitte, sur demande explicite de la ligne
    /// de commande. Une capture faite dans l'éditeur ne prouve rien du build :
    /// c'est précisément hors éditeur qu'un matériau non résolu sort en magenta.
    /// Outil de contrôle uniquement, refusé hors build Development.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class M1ScreenshotProbe : MonoBehaviour
    {
        public const string PathFlag = "--capture-screenshot";
        public const string DelayFlag = "--capture-after";
        public const string QuitFlag = "--capture-and-quit";

        private const float MinimumDelaySeconds = 0.5f;
        private const float MaximumDelaySeconds = 60f;
        private const float WriteTimeoutSeconds = 20f;

        private string _path;
        private float _delaySeconds = 5f;
        private bool _quitAfterCapture;

        private void Awake()
        {
            ParseCommandLine(Environment.GetCommandLineArgs());
        }

        private IEnumerator Start()
        {
            if (string.IsNullOrEmpty(_path))
                yield break;

            if (!Debug.isDebugBuild && !Application.isEditor)
            {
                Debug.LogError("[GAME-M1-SHOT] capture refusée hors build Development.");
                yield break;
            }

            // Temps réel assumé : cette sonde n'appartient pas à la simulation et
            // ne touche aucun état partagé, elle attend seulement que la scène,
            // la connexion et l'apparition du joueur soient visibles.
            yield return new WaitForSecondsRealtime(_delaySeconds);
            yield return new WaitForEndOfFrame();

            var directory = Path.GetDirectoryName(_path);
            if (!string.IsNullOrEmpty(directory))
                Directory.CreateDirectory(directory);
            ScreenCapture.CaptureScreenshot(_path);

            // L'écriture est asynchrone : sans attente, le processus peut quitter
            // avant que le fichier n'existe et la gate croirait à un échec.
            var deadline = Time.realtimeSinceStartup + WriteTimeoutSeconds;
            while (Time.realtimeSinceStartup < deadline &&
                   (!File.Exists(_path) || new FileInfo(_path).Length == 0))
            {
                yield return null;
            }

            if (File.Exists(_path) && new FileInfo(_path).Length > 0)
            {
                Debug.Log(
                    $"[GAME-M1-SHOT] captured file={_path} bytes={new FileInfo(_path).Length} " +
                    $"resolution={Screen.width}x{Screen.height}.");
            }
            else
                Debug.LogError($"[GAME-M1-SHOT] capture absente: {_path}.");

            if (_quitAfterCapture)
                Application.Quit();
        }

        private void ParseCommandLine(string[] arguments)
        {
            if (arguments == null)
                return;

            for (var index = 0; index < arguments.Length; index++)
            {
                if (string.Equals(arguments[index], QuitFlag, StringComparison.OrdinalIgnoreCase))
                    _quitAfterCapture = true;
                ReadArgument(arguments, ref index, PathFlag, value => _path = value);
                ReadArgument(arguments, ref index, DelayFlag, value =>
                {
                    if (float.TryParse(
                            value,
                            NumberStyles.Float,
                            CultureInfo.InvariantCulture,
                            out var parsed))
                    {
                        _delaySeconds = Mathf.Clamp(parsed, MinimumDelaySeconds, MaximumDelaySeconds);
                    }
                });
            }
        }

        private static void ReadArgument(
            string[] arguments,
            ref int index,
            string key,
            Action<string> apply)
        {
            var current = arguments[index];
            var prefix = key + "=";
            if (current.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            {
                apply(current.Substring(prefix.Length));
                return;
            }

            if (string.Equals(current, key, StringComparison.OrdinalIgnoreCase) &&
                index + 1 < arguments.Length)
            {
                index++;
                apply(arguments[index]);
            }
        }
    }
}
