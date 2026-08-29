using NotThatWay.Game.Input;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Menu pause local du banc, ouvert par Échap (qui libère le curseur et
    /// coupe déjà le regard) : à gauche les préférences de présentation —
    /// sensibilités, inversion Y, champ de vision, volume, limite d'images,
    /// plein écran — à droite le rappel complet des commandes, qui n'occupe
    /// plus l'écran de jeu. Tout est local et persisté en PlayerPrefs : rien
    /// n'entre dans une commande ni dans une règle partagée (ADR 0004), et la
    /// partie continue derrière le menu.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(PredictedPlayerMotor))]
    [RequireComponent(typeof(PlayerInputSource))]
    public sealed class M1PauseMenu : MonoBehaviour
    {
        private const string MouseKey = "game.look.mouse";
        private const string StickKey = "game.look.stick";
        private const string InvertKey = "game.look.invert";
        private const string FovKey = "game.camera.fov";
        private const string VolumeKey = "game.audio.master";
        private const string FrameLimitKey = "game.video.framelimit";

        private static readonly int[] FrameLimits = { -1, 30, 60, 120, 240 };
        private static readonly string[] FrameLimitLabels = { "VSync", "30", "60", "120", "240" };

        [SerializeField] private Camera _camera;

        private PredictedPlayerMotor _motor;
        private PlayerInputSource _inputSource;
        private Vector2 _controlsScroll;
        private float _mouseSensitivity = 1f;
        private float _stickSensitivity = 1f;
        private bool _invertPitch;
        private float _fieldOfView = 70f;
        private float _masterVolume = 1f;
        private int _frameLimitIndex = 2;
        private bool _wasOpen;

        private void Awake()
        {
            _motor = GetComponent<PredictedPlayerMotor>();
            _inputSource = GetComponent<PlayerInputSource>();
            LoadPreferences();
        }

        private void Start() => ApplyPreferences();

        private void Update()
        {
            // Sauvegarde une fois, quand le menu se referme (Échap ou Reprendre).
            var open = _motor != null && _motor.IsOwner && !_motor.CursorLocked;
            if (_wasOpen && !open)
                SavePreferences();
            _wasOpen = open;
        }

        private void LoadPreferences()
        {
            _mouseSensitivity = Mathf.Clamp(PlayerPrefs.GetFloat(MouseKey, 1f), 0.2f, 3f);
            _stickSensitivity = Mathf.Clamp(PlayerPrefs.GetFloat(StickKey, 1f), 0.2f, 3f);
            _invertPitch = PlayerPrefs.GetInt(InvertKey, 0) == 1;
            _fieldOfView = Mathf.Clamp(PlayerPrefs.GetFloat(FovKey, 70f), 60f, 90f);
            _masterVolume = Mathf.Clamp01(PlayerPrefs.GetFloat(VolumeKey, 1f));
            _frameLimitIndex = Mathf.Clamp(
                PlayerPrefs.GetInt(FrameLimitKey, 2),
                0,
                FrameLimits.Length - 1);
        }

        private void ApplyPreferences()
        {
            if (_inputSource != null)
            {
                _inputSource.PointerSensitivityMultiplier = _mouseSensitivity;
                _inputSource.StickSensitivityMultiplier = _stickSensitivity;
                _inputSource.InvertLookPitch = _invertPitch;
            }
            if (_camera != null && _motor != null && _motor.IsOwner)
                _camera.fieldOfView = _fieldOfView;
            AudioListener.volume = _masterVolume;
            var limit = FrameLimits[_frameLimitIndex];
            QualitySettings.vSyncCount = limit < 0 ? 1 : 0;
            Application.targetFrameRate = limit < 0 ? -1 : limit;
        }

        private void SavePreferences()
        {
            PlayerPrefs.SetFloat(MouseKey, _mouseSensitivity);
            PlayerPrefs.SetFloat(StickKey, _stickSensitivity);
            PlayerPrefs.SetInt(InvertKey, _invertPitch ? 1 : 0);
            PlayerPrefs.SetFloat(FovKey, _fieldOfView);
            PlayerPrefs.SetFloat(VolumeKey, _masterVolume);
            PlayerPrefs.SetInt(FrameLimitKey, _frameLimitIndex);
            PlayerPrefs.Save();
        }

        private void OnGUI()
        {
            if (_motor == null || !_motor.IsOwner || _motor.CursorLocked)
                return;

            var width = Mathf.Min(820f, Screen.width - 40f);
            var height = Mathf.Min(460f, Screen.height - 40f);
            var area = new Rect(
                (Screen.width - width) * 0.5f,
                (Screen.height - height) * 0.5f,
                width,
                height);
            GUI.Box(area, GUIContent.none);
            GUILayout.BeginArea(new Rect(area.x + 16f, area.y + 10f, width - 32f, height - 20f));
            GUILayout.Label(
                "<b>PAUSE (Échap)</b> — réglages et commandes ; la partie continue derrière",
                RichLabel());
            GUILayout.Space(6f);
            GUILayout.BeginHorizontal();
            GUILayout.BeginVertical(GUILayout.Width((width - 32f) * 0.46f));

            _mouseSensitivity = Slider(
                $"Sensibilité souris : {_mouseSensitivity:0.00}×",
                _mouseSensitivity, 0.2f, 3f);
            _stickSensitivity = Slider(
                $"Sensibilité manette : {_stickSensitivity:0.00}×",
                _stickSensitivity, 0.2f, 3f);
            _invertPitch = GUILayout.Toggle(_invertPitch, " Inverser l'axe vertical (Y)");
            _fieldOfView = Mathf.Round(Slider(
                $"Champ de vision : {_fieldOfView:0}°",
                _fieldOfView, 60f, 90f));
            _masterVolume = Slider(
                $"Volume général : {_masterVolume * 100f:0} %",
                _masterVolume, 0f, 1f);

            GUILayout.Space(4f);
            GUILayout.Label("Limite d'images :");
            _frameLimitIndex = GUILayout.Toolbar(_frameLimitIndex, FrameLimitLabels);

            var fullscreen = GUILayout.Toggle(Screen.fullScreen, " Plein écran (build)");
            if (fullscreen != Screen.fullScreen)
                Screen.fullScreen = fullscreen;

            GUILayout.FlexibleSpace();
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Reprendre (Échap)", GUILayout.Height(28f)))
                _motor.ResumeFromMenu();
            if (GUILayout.Button("Quitter le jeu", GUILayout.Height(28f), GUILayout.Width(130f)))
                Application.Quit();
            GUILayout.EndHorizontal();
            GUILayout.EndVertical();

            GUILayout.Space(14f);
            GUILayout.BeginVertical();
            GUILayout.Label("<b>COMMANDES</b>", RichLabel());
            _controlsScroll = GUILayout.BeginScrollView(_controlsScroll);
            for (var row = 0; row < M1ControlsOverlay.RowCount; row++)
            {
                var action = M1ControlsOverlay.ActionAt(row);
                GUILayout.BeginHorizontal();
                GUILayout.Label(
                    string.IsNullOrEmpty(action) ? " " : action,
                    GUILayout.Width(150f));
                GUILayout.Label(M1ControlsOverlay.BindingAt(row));
                GUILayout.EndHorizontal();
            }
            GUILayout.EndScrollView();
            GUILayout.EndVertical();
            GUILayout.EndHorizontal();
            GUILayout.EndArea();

            if (Event.current.type == EventType.Repaint)
                ApplyPreferences();
        }

        private static float Slider(string label, float value, float minimum, float maximum)
        {
            GUILayout.Label(label);
            return GUILayout.HorizontalSlider(value, minimum, maximum);
        }

        private static GUIStyle RichLabel()
        {
            var style = new GUIStyle(GUI.skin.label) { richText = true };
            return style;
        }
    }
}
