using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Table des commandes du banc M1, affichée par le menu pause (Échap) — plus
    /// aucun panneau permanent à l'écran. La table reste ici pour que chaque
    /// fonctionnalité continue d'y déclarer sa ligne au même endroit.
    /// </summary>
    public static class M1ControlsOverlay
    {


        private static readonly string[,] Controls =
        {
            { "Se déplacer", "ZQSD / flèches · stick gauche" },
            { "Regarder", "souris · stick droit" },
            { "Courir", "Maj · L3" },
            { "Sauter", "Espace · A/Croix" },
            { "Plonger en avant", "Ctrl ou C · LB/L1 — en sprintant vers l'avant" },
            { "Interagir / ramasser", "E · X/Carré" },
            { "Pousser le mur", "MAINTENIR E · X/Carré : il part" },
            { "", "au premier appui et s'écarte de vous" },
            // Doit suivre _minimumLeveragePermille du director : un panneau qui
            // annonce une force que la règle n'applique pas fausse le playtest.
            { "Force de poussée", "100 % au bout du battant, 40 % au gond" },
            { "Contre-pousser", "passer sur l'autre face et maintenir E" },
            { "Frapper / lancer", "F ou clic gauche · RT" },
            { "Lâcher l'objet", "A · B/Rond" },
            { "Cases d'objet", "1 / 2 / 3 · Tab ou R1 pour parcourir" },
            { "Vue 1re / 3e personne", "F1 · croix haut" },
            { "Zoomer (3e personne)", "molette · croix gauche/droite" },
            { "Pause / réglages", "Échap — sensibilité, FOV, volume…" }
        };

        /// <summary>Lignes action/touches, dans l'ordre d'affichage du menu pause.</summary>
        public static int RowCount => Controls.GetLength(0);

        public static string ActionAt(int row) => Controls[row, 0];

        public static string BindingAt(int row) => Controls[row, 1];
    }
}
