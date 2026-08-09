using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using NotThatWay.Game.Simulation;
using NotThatWay.Game.Topology;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Graybox runtime générée uniquement depuis une topologie signée. Les cubes
    /// fournissent rendu et BoxCollider ; aucun FBX, nom artistique ou MeshCollider
    /// n'entre dans la collision gameplay.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class TopologyArena : MonoBehaviour
    {
        [SerializeField] private TextAsset _topologyAsset;
        [SerializeField] private bool _buildOnAwake = true;

        private readonly Dictionary<int, TopologyWallView> _wallViews = new();
        private readonly Dictionary<int, int> _wallStates = new();
        private IReadOnlyDictionary<int, int> _wallStatesView;
        private Transform _generatedRoot;

        public TopologyRuntimeMap Map { get; private set; }
        public int WallCount => _wallViews.Count;
        public IReadOnlyDictionary<int, int> WallStates =>
            _wallStatesView ??= new ReadOnlyDictionary<int, int>(_wallStates);
        public Transform GeneratedRoot => _generatedRoot;

        private void Awake()
        {
            if (_buildOnAwake && _topologyAsset != null)
                BuildFromJson(_topologyAsset.text);
        }

        public void Configure(TextAsset topologyAsset, bool buildOnAwake = true)
        {
            _topologyAsset = topologyAsset;
            _buildOnAwake = buildOnAwake;
        }

        public void BuildFromConfiguredAsset()
        {
            if (_topologyAsset == null)
                throw new InvalidOperationException("Aucun TextAsset de topologie configure.");
            BuildFromJson(_topologyAsset.text);
        }

        public void BuildFromJson(string json)
        {
            GameplayLayers.ValidateProjectConfiguration();
            ValidateTopologyTransform();
            if (!TopologyRuntimeMap.TryCreateVerified(json, out var map, out var issues))
            {
                var first = issues.Count > 0 ? issues[0] : null;
                throw new InvalidOperationException(first == null
                    ? "Topologie runtime invalide."
                    : $"Topologie runtime invalide: {first.Code}@{first.Path}.");
            }

            ClearGenerated();
            Map = map;
            _wallViews.Clear();
            _wallStates.Clear();

            _generatedRoot = new GameObject($"Generated_{map.TopologyId}").transform;
            _generatedRoot.SetParent(transform, false);
            CreateFloor(map);
            CreateWalls(map);
            CreatePivots(map);
            CreateSpawns(map);
            Physics.SyncTransforms();
        }

        public TopologyWallView GetWallView(int wallId)
        {
            if (!_wallViews.TryGetValue(wallId, out var view))
                throw new ArgumentOutOfRangeException(nameof(wallId), wallId, "Mur absent de l'arene.");
            return view;
        }

        /// <summary>
        /// Applique une transition seulement après validation pure. La mutation est
        /// atomique : aucun état ni transform ne change lors d'un refus.
        /// </summary>
        public TopologyTransitionDecision TryGrayboxTransitionWall(
            int wallId,
            int stateId,
            IReadOnlyList<TopologyCircleObstacle> obstacles)
        {
            return TryTransitionWall(
                wallId,
                stateId,
                TopologyTransitionPolicy.GrayboxDuel,
                obstacles);
        }

        internal TopologyTransitionDecision TryTransitionWall(
            int wallId,
            int stateId,
            TopologyTransitionPolicy policy,
            IReadOnlyList<TopologyCircleObstacle> obstacles)
        {
            if (Map == null)
                throw new InvalidOperationException("L'arene n'est pas construite.");
            var decision = TopologyTransitionGuard.Evaluate(
                Map, _wallStates, wallId, stateId, policy, obstacles);
            if (decision.Allowed)
                ApplyAuthoritativeState(wallId, stateId);
            return decision;
        }

        /// <summary>
        /// Pose un état déjà validé par l'autorité (snapshot, reconcile ou reset).
        /// Une intention gameplay ne doit jamais appeler cette méthode directement.
        /// </summary>
        internal void ApplyAuthoritativeState(int wallId, int stateId)
        {
            ApplyAuthoritativeStateWithoutSync(wallId, stateId);
            Physics.SyncTransforms();
        }

        /// <summary>
        /// Pose le collider d'un mur au tick logique demandé. Pendant la transition,
        /// l'état d'occupation reste la pose source ; au dernier échantillon il
        /// bascule atomiquement sur la destination.
        /// </summary>
        internal void ApplyAuthoritativePose(
            int wallId,
            int logicalStateId,
            WallPoseSample pose)
        {
            if (Map == null)
                throw new InvalidOperationException("L'arene n'est pas construite.");
            var wall = Map.GetWall(wallId);
            wall.GetState(logicalStateId);
            if (pose.FromStateId != logicalStateId && pose.ToStateId != logicalStateId)
                throw new ArgumentException("Pose incohérente avec l'état logique.", nameof(pose));

            _wallViews[wallId].ApplyPose(pose);
            _wallStates[wallId] = pose.IsTransitioning
                ? logicalStateId
                : pose.ToStateId;
            Physics.SyncTransforms();
        }

        private void ApplyAuthoritativeStateWithoutSync(int wallId, int stateId)
        {
            var wall = Map?.GetWall(wallId) ?? throw new InvalidOperationException("L'arene n'est pas construite.");
            wall.GetState(stateId);
            _wallViews[wallId].ApplyState(stateId);
            _wallStates[wallId] = stateId;
        }

        public void ResetToInitialStates()
        {
            if (Map == null)
                throw new InvalidOperationException("L'arene n'est pas construite.");
            foreach (var wall in Map.Walls)
                ApplyAuthoritativeStateWithoutSync(wall.WallId, wall.InitialStateId);
            Physics.SyncTransforms();
        }

        /// <summary>
        /// Quantifie un obstacle monde dans l'espace local millimétrique de la
        /// topologie. L'autorité serveur doit construire elle-même cette liste.
        /// </summary>
        public TopologyCircleObstacle CreateObstacleFromWorld(
            int obstacleId,
            Vector3 worldCenter,
            float radiusMeters)
        {
            ValidateTopologyTransform();
            if (float.IsNaN(radiusMeters) || float.IsInfinity(radiusMeters) || radiusMeters < 0f)
                throw new ArgumentOutOfRangeException(nameof(radiusMeters));

            var localCenter = transform.InverseTransformPoint(worldCenter);
            var centerXMm = QuantizeMillimeters(localCenter.x, nameof(worldCenter));
            var centerZMm = QuantizeMillimeters(localCenter.z, nameof(worldCenter));
            var radiusMmDouble = Math.Ceiling(radiusMeters * 1000d) + 1d;
            if (radiusMmDouble > int.MaxValue)
                throw new ArgumentOutOfRangeException(nameof(radiusMeters));
            return new TopologyCircleObstacle(
                obstacleId,
                centerXMm,
                centerZMm,
                (int)radiusMmDouble);
        }

        public bool HasOnlyPrimitiveGameplayColliders()
        {
            if (_generatedRoot == null || _generatedRoot.GetComponentsInChildren<MeshCollider>(true).Length != 0)
                return false;
            return _generatedRoot.GetComponentsInChildren<Collider>(true)
                .Where(value => value.enabled)
                .All(value => value is BoxCollider && value.gameObject.layer == GameplayLayers.World);
        }

        private void CreateFloor(TopologyRuntimeMap map)
        {
            const float floorThickness = 0.2f;
            var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.name = "Floor";
            floor.layer = GameplayLayers.World;
            floor.transform.SetParent(_generatedRoot, false);
            floor.transform.localPosition = new Vector3(0f, -floorThickness * 0.5f, 0f);
            floor.transform.localScale = new Vector3(
                (float)((double)map.Dimensions.WidthCells * map.Dimensions.CellPitchMm / 1000d),
                floorThickness,
                (float)((double)map.Dimensions.HeightCells * map.Dimensions.CellPitchMm / 1000d));
            SetColor(floor, new Color(0.19f, 0.21f, 0.24f));
        }

        private void CreateWalls(TopologyRuntimeMap map)
        {
            var wallRoot = new GameObject("Walls").transform;
            wallRoot.SetParent(_generatedRoot, false);
            foreach (var wall in map.Walls)
            {
                var wallObject = GameObject.CreatePrimitive(PrimitiveType.Cube);
                wallObject.name = $"Wall_{wall.WallId}";
                wallObject.layer = GameplayLayers.World;
                wallObject.transform.SetParent(wallRoot, false);
                var view = wallObject.AddComponent<TopologyWallView>();
                view.Initialize(map, wall);
                SetColor(wallObject, wall.IsMobile
                    ? new Color(0.10f, 0.78f, 0.88f)
                    : new Color(0.48f, 0.52f, 0.58f));
                _wallViews.Add(wall.WallId, view);
                _wallStates.Add(wall.WallId, wall.InitialStateId);
            }
        }

        private void CreatePivots(TopologyRuntimeMap map)
        {
            var pivotRoot = new GameObject("Pivots").transform;
            pivotRoot.SetParent(_generatedRoot, false);
            foreach (var pivot in map.Pivots)
            {
                var marker = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                marker.name = $"Pivot_{pivot.PivotId}";
                marker.layer = GameplayLayers.VisualOnly;
                marker.transform.SetParent(pivotRoot, false);
                var point = TopologyGeometry.NodeMm(map, pivot.NodeX, pivot.NodeY).Meters;
                marker.transform.localPosition = point + Vector3.up * 0.05f;
                marker.transform.localScale = new Vector3(0.45f, 0.05f, 0.45f);
                DisableCollider(marker);
                SetColor(marker, new Color(1f, 0.55f, 0.05f));
            }
        }

        private void CreateSpawns(TopologyRuntimeMap map)
        {
            var spawnRoot = new GameObject("Spawns").transform;
            spawnRoot.SetParent(_generatedRoot, false);
            foreach (var spawn in map.Spawns)
            {
                var point = new GameObject($"Spawn_{spawn.SpawnId}").transform;
                point.SetParent(spawnRoot, false);
                point.localPosition = TopologyGeometry.CellCenterMm(map, spawn.Cell).Meters;
                point.localRotation = Quaternion.Euler(0f, spawn.YawQuarterTurns * 90f, 0f);

                var marker = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                marker.name = "Marker";
                marker.layer = GameplayLayers.VisualOnly;
                marker.transform.SetParent(point, false);
                marker.transform.localPosition = Vector3.up * 0.025f;
                marker.transform.localScale = new Vector3(0.35f, 0.025f, 0.35f);
                DisableCollider(marker);
                SetColor(marker, spawn.SpawnId % 2 == 0
                    ? new Color(0.30f, 0.95f, 0.35f)
                    : new Color(0.95f, 0.25f, 0.45f));
            }
        }

        private void ClearGenerated()
        {
            if (_generatedRoot == null)
                return;
            if (Application.isPlaying)
            {
                // Destroy est différé jusqu'à la fin de frame. Désactiver d'abord
                // retire immédiatement l'ancienne collision de la simulation.
                _generatedRoot.gameObject.SetActive(false);
                Destroy(_generatedRoot.gameObject);
            }
            else
                DestroyImmediate(_generatedRoot.gameObject);
            _generatedRoot = null;
        }

        private static void DisableCollider(GameObject value)
        {
            if (value.TryGetComponent<Collider>(out var collider))
                collider.enabled = false;
        }

        private static void SetColor(GameObject value, Color color)
        {
            if (value.TryGetComponent<Renderer>(out var renderer))
            {
                var properties = new MaterialPropertyBlock();
                renderer.GetPropertyBlock(properties);
                properties.SetColor("_BaseColor", color);
                properties.SetColor("_Color", color);
                renderer.SetPropertyBlock(properties);
            }
        }

        private void ValidateTopologyTransform()
        {
            var scale = transform.lossyScale;
            const float tolerance = 0.0001f;
            if (!IsFinite(scale.x) || !IsFinite(scale.y) || !IsFinite(scale.z) ||
                Mathf.Abs(scale.x - 1f) > tolerance ||
                Mathf.Abs(scale.y - 1f) > tolerance ||
                Mathf.Abs(scale.z - 1f) > tolerance)
            {
                throw new InvalidOperationException(
                    "TopologyArena exige une échelle monde uniforme 1; position et rotation restent supportées.");
            }
        }

        private static int QuantizeMillimeters(float meters, string parameterName)
        {
            if (float.IsNaN(meters) || float.IsInfinity(meters))
                throw new ArgumentOutOfRangeException(parameterName);
            var millimeters = Math.Round(meters * 1000d, MidpointRounding.AwayFromZero);
            if (millimeters < int.MinValue || millimeters > int.MaxValue)
                throw new ArgumentOutOfRangeException(parameterName);
            return (int)millimeters;
        }

        private static bool IsFinite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
    }
}
