using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Un mur droit du labyrinthe qui pivote sur un de ses bouts, comme une porte
    /// lourde. Un quart de tour le fait changer d'axe : un mur nord-sud devient
    /// est-ouest, et vient se poser exactement sur l'arête voisine — la grille est
    /// carrée et un mur fait un pas de long, donc aucune pose intermédiaire n'est
    /// possible.
    ///
    /// Tout ce que porte ce composant vient de la topologie typée
    /// `MazeGrid16x16.json` et non du FBX : l'identifiant, l'arête d'origine et le
    /// collider. Le maillage n'est qu'un habillage découpé sur la même grille ; ni
    /// son nom, ni ses triangles, ni sa place dans la hiérarchie ne définissent une
    /// règle ou un identifiant réseau (ADR 0004).
    ///
    /// Les index reprennent ceux de la grille : la famille 0 est une arête
    /// verticale `vwalls[x][y]`, qui va du nœud <c>(x, y)</c> au nœud
    /// <c>(x, y + 1)</c> ; la famille 1 est une arête horizontale `hwalls[x][y]`,
    /// du nœud <c>(x, y)</c> au nœud <c>(x + 1, y)</c>. Ce sont les bouts communs
    /// entre deux arêtes qui servent de gond.
    ///
    /// La position et l'orientation courantes ne sont pas ici : elles appartiennent
    /// à <see cref="MovableWallDirector"/>, qui en est seul responsable et les
    /// réplique.
    /// </summary>
    public sealed class MovableWall : MonoBehaviour
    {
        [SerializeField] private int _id = -1;
        [SerializeField] private int _homeFamily;
        [SerializeField] private int _homeSlotX;
        [SerializeField] private int _homeSlotY;

        /// <summary>Rang dans l'état répliqué par <see cref="MovableWallDirector"/>.</summary>
        public int Id => _id;

        /// <summary>0 pour une arête verticale de la grille, 1 pour une horizontale.</summary>
        public int HomeFamily => _homeFamily;

        /// <summary>Index de l'arête d'origine, en coordonnées de grille.</summary>
        public int HomeSlotX => _homeSlotX;

        /// <summary>Index de l'arête d'origine, en coordonnées de grille.</summary>
        public int HomeSlotY => _homeSlotY;
    }
}
