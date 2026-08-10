using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Marque un mur pivotant du décor, conserve son <c>pivotId</c> canonique et
    /// porte encore le rang contigu consommé par le <see cref="PivotDirector"/>
    /// historique. Ce rang est trié par ID de topologie, jamais par nom FBX.
    /// </summary>
    public sealed class PivotWall : MonoBehaviour
    {
        [SerializeField] private int _index = -1;
        [SerializeField] private int _pivotId = -1;

        public int Index => _index;
        public int PivotId => _pivotId;
    }
}
