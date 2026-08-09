using System;
using NotThatWay.Game.Topology;
using UnityEngine;

namespace NotThatWay.Game
{
    [DisallowMultipleComponent]
    [RequireComponent(typeof(BoxCollider))]
    public sealed class TopologyWallView : MonoBehaviour
    {
        [SerializeField] private int _wallId;
        [SerializeField] private int _pivotId = -1;
        [SerializeField] private int _stateId;

        private TopologyRuntimeMap _map;
        private RuntimeWallDefinition _definition;

        public int WallId => _wallId;
        public int? PivotId => _pivotId > 0 ? _pivotId : null;
        public int StateId => _stateId;
        public bool IsMobile => _definition?.IsMobile ?? _pivotId > 0;

        internal void Initialize(TopologyRuntimeMap map, RuntimeWallDefinition definition)
        {
            _map = map ?? throw new ArgumentNullException(nameof(map));
            _definition = definition ?? throw new ArgumentNullException(nameof(definition));
            _wallId = definition.WallId;
            _pivotId = definition.PivotId ?? -1;
            ApplyState(definition.InitialStateId);
        }

        internal void ApplyState(int stateId)
        {
            if (_map == null || _definition == null)
                throw new InvalidOperationException("Le mur doit etre initialise avant de recevoir un etat.");
            var spec = TopologyGeometry.WallBox(_map, _wallId, stateId);
            transform.localPosition = spec.CenterMeters;
            transform.localRotation = Quaternion.identity;
            transform.localScale = spec.SizeMeters;
            _stateId = stateId;
        }
    }
}
