using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;

namespace NotThatWay.Game.Topology
{
    public enum TopologyAxis : byte
    {
        Vertical = 0,
        Horizontal = 1
    }

    public readonly struct TopologyEdgeKey : IEquatable<TopologyEdgeKey>
    {
        public TopologyEdgeKey(TopologyAxis axis, int x, int y)
        {
            Axis = axis;
            X = x;
            Y = y;
        }

        public TopologyAxis Axis { get; }
        public int X { get; }
        public int Y { get; }

        public bool Equals(TopologyEdgeKey other) => Axis == other.Axis && X == other.X && Y == other.Y;
        public override bool Equals(object value) => value is TopologyEdgeKey other && Equals(other);
        public override int GetHashCode() => ((int)Axis * 397 ^ X) * 397 ^ Y;
        public override string ToString() => $"{Axis}:{X}:{Y}";
    }

    public readonly struct TopologyGridCell : IEquatable<TopologyGridCell>
    {
        public TopologyGridCell(int x, int y)
        {
            X = x;
            Y = y;
        }

        public int X { get; }
        public int Y { get; }

        public bool Equals(TopologyGridCell other) => X == other.X && Y == other.Y;
        public override bool Equals(object value) => value is TopologyGridCell other && Equals(other);
        public override int GetHashCode() => X * 397 ^ Y;
        public override string ToString() => $"{X},{Y}";
    }

    public readonly struct RuntimeTopologyDimensions
    {
        public RuntimeTopologyDimensions(TopologyDimensions source)
        {
            WidthCells = source.WidthCells;
            HeightCells = source.HeightCells;
            CellPitchMm = source.CellPitchMm;
            WallThicknessMm = source.WallThicknessMm;
            WallHeightMm = source.WallHeightMm;
        }

        public int WidthCells { get; }
        public int HeightCells { get; }
        public int CellPitchMm { get; }
        public int WallThicknessMm { get; }
        public int WallHeightMm { get; }
    }

    public sealed class RuntimeWallStateDefinition
    {
        internal RuntimeWallStateDefinition(TopologyWallState source)
        {
            StateId = source.StateId;
            Edge = TopologyRuntimeMap.CopyEdge(source.Edge);
            QuarterTurns = source.QuarterTurns;
        }

        public int StateId { get; }
        public TopologyEdgeKey Edge { get; }
        public int QuarterTurns { get; }
    }

    public sealed class RuntimeWallDefinition
    {
        private readonly ReadOnlyCollection<RuntimeWallStateDefinition> _states;
        private readonly ReadOnlyDictionary<int, RuntimeWallStateDefinition> _statesById;

        internal RuntimeWallDefinition(TopologyWall source)
        {
            WallId = source.WallId;
            PivotId = source.PivotId;
            InitialStateId = source.InitialStateId;
            var states = source.States
                .OrderBy(value => value.StateId)
                .Select(value => new RuntimeWallStateDefinition(value))
                .ToList();
            _states = states.AsReadOnly();
            _statesById = new ReadOnlyDictionary<int, RuntimeWallStateDefinition>(
                states.ToDictionary(value => value.StateId));
        }

        public int WallId { get; }
        public int? PivotId { get; }
        public int InitialStateId { get; }
        public IReadOnlyList<RuntimeWallStateDefinition> States => _states;
        public bool IsMobile => PivotId.HasValue;

        public bool TryGetState(int stateId, out RuntimeWallStateDefinition state) =>
            _statesById.TryGetValue(stateId, out state);

        public RuntimeWallStateDefinition GetState(int stateId)
        {
            if (!_statesById.TryGetValue(stateId, out var state))
                throw new ArgumentOutOfRangeException(nameof(stateId), stateId, $"Etat absent du mur {WallId}.");
            return state;
        }
    }

    public sealed class RuntimePivotDefinition
    {
        private readonly ReadOnlyCollection<int> _wallIds;

        internal RuntimePivotDefinition(TopologyPivot source)
        {
            PivotId = source.PivotId;
            NodeX = source.Node.X;
            NodeY = source.Node.Y;
            _wallIds = source.WallIds.OrderBy(value => value).ToList().AsReadOnly();
        }

        public int PivotId { get; }
        public int NodeX { get; }
        public int NodeY { get; }
        public IReadOnlyList<int> WallIds => _wallIds;
    }

    public sealed class RuntimeOpeningDefinition
    {
        internal RuntimeOpeningDefinition(TopologyOpening source)
        {
            OpeningId = source.OpeningId;
            Edge = TopologyRuntimeMap.CopyEdge(source.Edge);
        }

        public int OpeningId { get; }
        public TopologyEdgeKey Edge { get; }
    }

    public sealed class RuntimeSpawnDefinition
    {
        internal RuntimeSpawnDefinition(TopologySpawn source)
        {
            SpawnId = source.SpawnId;
            Cell = new TopologyGridCell(source.Cell.X, source.Cell.Y);
            YawQuarterTurns = source.YawQuarterTurns;
        }

        public int SpawnId { get; }
        public TopologyGridCell Cell { get; }
        public int YawQuarterTurns { get; }
    }

    /// <summary>
    /// Copie immuable du DTO JSON vérifié. Une mutation accidentelle du document
    /// Newtonsoft ne peut donc jamais désynchroniser le checksum du runtime.
    /// </summary>
    public sealed class TopologyRuntimeMap
    {
        private readonly ReadOnlyCollection<RuntimeWallDefinition> _walls;
        private readonly ReadOnlyCollection<RuntimePivotDefinition> _pivots;
        private readonly ReadOnlyCollection<RuntimeSpawnDefinition> _spawns;
        private readonly ReadOnlyCollection<RuntimeOpeningDefinition> _openings;
        private readonly ReadOnlyDictionary<int, RuntimeWallDefinition> _wallsById;
        private readonly ReadOnlyDictionary<int, RuntimePivotDefinition> _pivotsById;

        private TopologyRuntimeMap(TopologyDocument source)
        {
            SchemaVersion = source.SchemaVersion;
            TopologyId = source.TopologyId;
            Checksum = source.Checksum;
            Dimensions = new RuntimeTopologyDimensions(source.Dimensions);

            var walls = source.Walls.OrderBy(value => value.WallId)
                .Select(value => new RuntimeWallDefinition(value)).ToList();
            var pivots = source.Pivots.OrderBy(value => value.PivotId)
                .Select(value => new RuntimePivotDefinition(value)).ToList();
            var spawns = source.Spawns.OrderBy(value => value.SpawnId)
                .Select(value => new RuntimeSpawnDefinition(value)).ToList();
            var openings = source.Openings.OrderBy(value => value.OpeningId)
                .Select(value => new RuntimeOpeningDefinition(value)).ToList();

            _walls = walls.AsReadOnly();
            _pivots = pivots.AsReadOnly();
            _spawns = spawns.AsReadOnly();
            _openings = openings.AsReadOnly();
            _wallsById = new ReadOnlyDictionary<int, RuntimeWallDefinition>(
                walls.ToDictionary(value => value.WallId));
            _pivotsById = new ReadOnlyDictionary<int, RuntimePivotDefinition>(
                pivots.ToDictionary(value => value.PivotId));
        }

        public int SchemaVersion { get; }
        public string TopologyId { get; }
        public string Checksum { get; }
        public RuntimeTopologyDimensions Dimensions { get; }
        public IReadOnlyList<RuntimeWallDefinition> Walls => _walls;
        public IReadOnlyList<RuntimePivotDefinition> Pivots => _pivots;
        public IReadOnlyList<RuntimeSpawnDefinition> Spawns => _spawns;
        public IReadOnlyList<RuntimeOpeningDefinition> Openings => _openings;

        public static bool TryCreateVerified(
            string json,
            out TopologyRuntimeMap map,
            out IReadOnlyList<TopologyIssue> issues)
        {
            var parsed = TopologyParser.ParseVerified(json);
            issues = parsed.Issues;
            if (!parsed.IsValid)
            {
                map = null;
                return false;
            }

            map = new TopologyRuntimeMap(parsed.Document);
            return true;
        }

        public RuntimeWallDefinition GetWall(int wallId)
        {
            if (!_wallsById.TryGetValue(wallId, out var wall))
                throw new ArgumentOutOfRangeException(nameof(wallId), wallId, "Mur absent de la topologie.");
            return wall;
        }

        public RuntimePivotDefinition GetPivot(int pivotId)
        {
            if (!_pivotsById.TryGetValue(pivotId, out var pivot))
                throw new ArgumentOutOfRangeException(nameof(pivotId), pivotId, "Pivot absent de la topologie.");
            return pivot;
        }

        public Dictionary<int, int> CreateInitialWallStates()
        {
            return _walls.ToDictionary(value => value.WallId, value => value.InitialStateId);
        }

        internal static TopologyEdgeKey CopyEdge(TopologyEdge source)
        {
            return new TopologyEdgeKey(
                source.Axis == TopologyEdge.VerticalAxis ? TopologyAxis.Vertical : TopologyAxis.Horizontal,
                source.X,
                source.Y);
        }
    }
}
