using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Rappel permanent des commandes du banc M1. Un testeur qui cherche la touche
    /// ne teste plus le réseau. Affichage local uniquement : aucun état partagé,
    /// aucune règle, aucun tick. Le repli passe par un bouton IMGUI et non par une
    /// lecture clavier directe, interdite hors Input Actions.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class M1ControlsOverlay : MonoBehaviour
    {
        private const float PanelWidth = 500f;
        private const float PanelMargin = 16f;
        private const float ActionColumnWidth = 160f;

        // Hauteur réelle d'une ligne GUILayout à cette taille de police, marge et
        // remplissage de la boîte compris. Sous-estimer coupe le bouton de repli
        // dans le player : mesuré sur la capture de contrôle, pas estimé.
        private const float LineHeight = 22f;
        private const float HeaderHeight = 40f;
        private const float ButtonHeight = 34f;
        private const float CollapsedWidth = 150f;
        private const float CollapsedHeight = 46f;

        private static readonly string[,] Controls =
        {
            { "Se déplacer", "ZQSD / WASD · stick gauche" },
            { "Regarder", "souris · stick droit" },
            { "Courir", "Maj · L3" },
            { "Pousser le mur", "MAINTENIR E (clic gauche · RT) : il part" },
            { "", "au premier appui et s'écarte de vous" },
            // Doit suivre _minimumLeveragePermille du director : un panneau qui
            // annonce une force que la règle n'applique pas fausse le playtest.
            { "Force de poussée", "100 % au bout du battant, 40 % au gond" },
            { "Contre-pousser", "passer sur l'autre face et maintenir E" },
            { "Frapper", "F ou clic droit · R1 — pousse le mur aussi" },
            { "Vue 1re / 3e personne", "F1 · croix haut" },
            { "Zoomer (3e personne)", "molette · croix gauche/droite" },
            { "Libérer le curseur", "Échap" }
        };

        private bool _expanded = true;
        private GUIStyle _titleStyle;
        private GUIStyle _actionStyle;
        private GUIStyle _bindingStyle;

        private void OnGUI()
        {
            EnsureStyles();
            if (!_expanded)
            {
                var collapsed = new Rect(
                    PanelMargin,
                    Screen.height - CollapsedHeight - PanelMargin,
                    Mathf.Min(CollapsedWidth, Screen.width - PanelMargin * 2f),
                    CollapsedHeight);
                GUILayout.BeginArea(collapsed, GUI.skin.box);
                if (GUILayout.Button("COMMANDES"))
                    _expanded = true;
                GUILayout.EndArea();
                return;
            }

            var rows = Controls.GetLength(0);
            var height = HeaderHeight + rows * LineHeight + ButtonHeight;
            var area = new Rect(
                PanelMargin,
                Screen.height - height - PanelMargin,
                Mathf.Min(PanelWidth, Screen.width - PanelMargin * 2f),
                height);

            GUILayout.BeginArea(area, GUI.skin.box);
            GUILayout.Label("COMMANDES — banc M1", _titleStyle);
            for (var row = 0; row < rows; row++)
            {
                GUILayout.BeginHorizontal();
                GUILayout.Label(Controls[row, 0], _actionStyle, GUILayout.Width(ActionColumnWidth));
                GUILayout.Label(Controls[row, 1], _bindingStyle);
                GUILayout.EndHorizontal();
            }

            // Le curseur est capturé pendant le jeu : Échap le libère, puis ce
            // bouton replie le cadre.
            if (GUILayout.Button("MASQUER"))
                _expanded = false;
            GUILayout.EndArea();
        }

        private void EnsureStyles()
        {
            // Un GUIStyle ne survit pas à un rechargement de domaine : il se
            // construit à la première frame de rendu, pas dans Awake.
            _titleStyle ??= new GUIStyle(GUI.skin.label)
            {
                fontSize = 13,
                fontStyle = FontStyle.Bold
            };
            _actionStyle ??= new GUIStyle(GUI.skin.label) { fontSize = 12 };
            _bindingStyle ??= new GUIStyle(GUI.skin.label)
            {
                fontSize = 12,
                fontStyle = FontStyle.Bold
            };
        }
    }
}
