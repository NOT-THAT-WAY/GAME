using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Marque un mur pivotant du décor et porte son rang dans l'état répliqué par
    /// <see cref="PivotDirector"/>. L'index est posé à la génération de la scène,
    /// par ordre de nom, pour que toutes les machines numérotent les pivots
    /// pareil sans avoir à s'échanger la carte.
    /// </summary>
    public sealed class PivotWall : MonoBehaviour
    {
        [SerializeField] private int _index = -1;

        public int Index => _index;
    }
}
