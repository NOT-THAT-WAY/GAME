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
            ApplyPose(WallPoseSample.Stable(stateId));
        }

        internal void ApplyPose(WallPoseSample pose)
        {
            if (_map == null || _definition == null)
                throw new InvalidOperationException("Le mur doit etre initialise avant de recevoir une pose.");

            var from = _definition.GetState(pose.FromStateId);
            var to = _definition.GetState(pose.ToStateId);
            var fromSpec = TopologyGeometry.WallBox(_map, _wallId, pose.FromStateId);
            var toSpec = TopologyGeometry.WallBox(_map, _wallId, pose.ToStateId);
            var progress = pose.ProgressQ16 / (float)TickMath.CompleteProgressQ16;

            if (pose.FromStateId == pose.ToStateId)
            {
                transform.localPosition = fromSpec.CenterMeters;
                transform.localRotation = Quaternion.Euler(0f, from.QuarterTurns * 90f, 0f);
                transform.localScale = UnrotatedScale(fromSpec, from.QuarterTurns);
                _stateId = pose.FromStateId;
                return;
            }

            if (!_definition.PivotId.HasValue)
                throw new InvalidOperationException($"Le mur statique {_wallId} ne peut pas transiter.");
            var delta = (to.QuarterTurns - from.QuarterTurns + 4) % 4;
            if (delta != 1 && delta != 3)
                throw new InvalidOperationException("Une transition graybox doit être un quart de tour.");
            var signedQuarterTurn = delta == 1 ? 1f : -1f;
            var pivot = _map.GetPivot(_definition.PivotId.Value);
            var pivotPosition = TopologyGeometry.NodeMm(_map, pivot.NodeX, pivot.NodeY).Meters;
            pivotPosition.y = fromSpec.CenterMeters.y;
            var rotationDelta = Quaternion.Euler(0f, signedQuarterTurn * 90f * progress, 0f);

            transform.localPosition = pivotPosition +
                                      rotationDelta * (fromSpec.CenterMeters - pivotPosition);
            transform.localRotation = Quaternion.Euler(
                0f,
                (from.QuarterTurns + signedQuarterTurn * progress) * 90f,
                0f);
            transform.localScale = Vector3.Lerp(
                UnrotatedScale(fromSpec, from.QuarterTurns),
                UnrotatedScale(toSpec, to.QuarterTurns),
                progress);
            _stateId = pose.IsTransitioning ? pose.FromStateId : pose.ToStateId;
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
