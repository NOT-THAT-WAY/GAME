using System;
using NotThatWay.Game.Simulation;
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
        [SerializeField] private int _angleMilliDegrees;

        private TopologyRuntimeMap _map;
        private RuntimeWallDefinition _definition;
        private Vector3 _bladePivotPosition;
        private Vector3 _bladeAnchorPosition;
        private Vector3 _bladeScale;
        private float _bladeAnchorYaw;

        public int WallId => _wallId;
        public int? PivotId => _pivotId > 0 ? _pivotId : null;
        public int StateId => _stateId;

        /// <summary>Angle courant du battant, nul pour un mur statique.</summary>
        public int AngleMilliDegrees => _angleMilliDegrees;

        public bool IsMobile => _definition?.IsMobile ?? _pivotId > 0;

        internal void Initialize(TopologyRuntimeMap map, RuntimeWallDefinition definition)
        {
            _map = map ?? throw new ArgumentNullException(nameof(map));
            _definition = definition ?? throw new ArgumentNullException(nameof(definition));
            _wallId = definition.WallId;
            _pivotId = definition.PivotId ?? -1;

            if (definition.IsMobile)
            {
                // Le repère du battant est figé une fois : sa pose initiale déclarée
                // est l'angle zéro, et chaque tick n'y applique qu'une rotation.
                var anchor = TopologyGeometry.WallBox(map, _wallId, definition.InitialStateId);
                var anchorState = definition.GetState(definition.InitialStateId);
                var pivot = map.GetPivot(definition.PivotId.Value);
                _bladePivotPosition = TopologyGeometry.NodeMm(map, pivot.NodeX, pivot.NodeY).Meters;
                _bladePivotPosition.y = anchor.CenterMeters.y;
                _bladeAnchorPosition = anchor.CenterMeters;
                _bladeAnchorYaw = anchorState.QuarterTurns * 90f;
                _bladeScale = UnrotatedScale(anchor, anchorState.QuarterTurns);
                ApplyRotation(0);
                return;
            }

            ApplyState(definition.InitialStateId);
        }

        internal void ApplyState(int stateId)
        {
            if (_map == null || _definition == null)
                throw new InvalidOperationException("Le mur doit etre initialise avant de recevoir un etat.");
            if (_definition.IsMobile)
            {
                ApplyRotation(TopologyGeometry.StateAngleMilliDegrees(_map, _wallId, stateId));
                _stateId = stateId;
                return;
            }

            var state = _definition.GetState(stateId);
            var spec = TopologyGeometry.WallBox(_map, _wallId, stateId);
            transform.localPosition = spec.CenterMeters;
            transform.localRotation = Quaternion.Euler(0f, state.QuarterTurns * 90f, 0f);
            transform.localScale = UnrotatedScale(spec, state.QuarterTurns);
            _stateId = stateId;
        }

        internal void ApplyPose(WallPoseSample pose) => ApplyRotation(pose.AngleMilliDegrees);

        /// <summary>
        /// Pose le battant à l'angle autoritaire du tick. La rotation est cosmétique
        /// et collisionnelle à la fois : le BoxCollider suit le même transform, donc
        /// la même donnée entière, jamais une interpolation d'image.
        /// </summary>
        internal void ApplyRotation(int angleMilliDegrees)
        {
            if (_map == null || _definition == null)
                throw new InvalidOperationException("Le mur doit etre initialise avant de recevoir une pose.");
            if (!_definition.IsMobile)
                throw new InvalidOperationException($"Le mur statique {_wallId} ne peut pas tourner.");

            var normalized = FixedTrigonometry.Normalize(angleMilliDegrees);
            var degrees = normalized / 1000f;
            var rotation = Quaternion.Euler(0f, degrees, 0f);
            transform.localPosition = _bladePivotPosition +
                                      rotation * (_bladeAnchorPosition - _bladePivotPosition);
            transform.localRotation = Quaternion.Euler(0f, _bladeAnchorYaw + degrees, 0f);
            transform.localScale = _bladeScale;
            _angleMilliDegrees = normalized;
        }

        private static Vector3 UnrotatedScale(TopologyWallBoxSpec spec, int quarterTurns)
        {
            var size = spec.SizeMeters;
            var normalized = (quarterTurns % 4 + 4) % 4;
            return normalized % 2 == 0
                ? size
                : new Vector3(size.z, size.y, size.x);
        }
    }
}
