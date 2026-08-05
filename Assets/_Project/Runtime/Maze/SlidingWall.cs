using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Un mur droit du labyrinthe qui peut coulisser le long de son propre axe.
    ///
    /// Tout ce que porte ce composant vient de la topologie typée
    /// `MazeGrid16x16.json` et non du FBX : l'identifiant, la case d'arête
    /// d'origine, le pas de glissement et le collider. Le maillage n'est qu'un
    /// habillage découpé sur la même grille ; ni son nom, ni ses triangles, ni sa
    /// place dans la hiérarchie ne définissent une règle ou un identifiant
    /// réseau (ADR 0004).
    ///
    /// Les index de case reprennent ceux de la grille : la famille 0 est une
    /// arête verticale `vwalls[x][y]`, posée sur le nœud <c>x</c> et longue d'une
    /// cellule en <c>y</c> ; la famille 1 est une arête horizontale
    /// `hwalls[x][y]`, posée sur le nœud <c>y</c> et longue d'une cellule en
    /// <c>x</c>. Un mur ne glisse que dans sa propre famille, le long de sa
    /// longueur, donc en changeant le seul index qui court sur les cellules.
    /// </summary>
    public sealed class SlidingWall : MonoBehaviour
    {
        [SerializeField] private int _id = -1;
        [SerializeField] private int _family;
        [SerializeField] private int _slotX;
        [SerializeField] private int _slotY;
        [SerializeField] private Vector3 _home;
        [SerializeField] private Vector3 _step;

        /// <summary>Rang dans l'état répliqué par <see cref="SlidingWallDirector"/>.</summary>
        public int Id => _id;

        /// <summary>0 pour une arête verticale de la grille, 1 pour une horizontale.</summary>
        public int Family => _family;

        /// <summary>Index de case d'origine, en coordonnées de grille.</summary>
        public int SlotX => _slotX;

        /// <summary>Index de case d'origine, en coordonnées de grille.</summary>
        public int SlotY => _slotY;

        /// <summary>Déplacement monde d'un cran de grille, vers les index croissants.</summary>
        public Vector3 Step => _step;

        /// <summary>Position monde correspondant à un décalage entier de cases.</summary>
        public Vector3 PositionForOffset(int offset)
        {
            return _home + _step * offset;
        }
    }
}
