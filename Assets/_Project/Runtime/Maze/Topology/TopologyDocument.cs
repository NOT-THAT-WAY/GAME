using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace NotThatWay.Game.Topology
{
    [Serializable]
    [JsonObject(MemberSerialization.OptIn)]
    public sealed class TopologyDocument
    {
        [JsonProperty("schemaVersion", Required = Required.Always)]
        public int SchemaVersion { get; set; }

        [JsonProperty("topologyId", Required = Required.Always)]
        public string TopologyId { get; set; }

        [JsonProperty("dimensions", Required = Required.Always)]
        public TopologyDimensions Dimensions { get; set; }

        [JsonProperty("openings", Required = Required.Always)]
        public List<TopologyOpening> Openings { get; set; } = new();

        [JsonProperty("walls", Required = Required.Always)]
        public List<TopologyWall> Walls { get; set; } = new();

        [JsonProperty("pivots", Required = Required.Always)]
        public List<TopologyPivot> Pivots { get; set; } = new();

        [JsonProperty("spawns", Required = Required.Always)]
        public List<TopologySpawn> Spawns { get; set; } = new();

        /// <summary>SHA-256 des bytes canoniques, qui excluent ce champ.</summary>
        [JsonProperty("checksum")]
        public string Checksum { get; set; }
    }

    [Serializable]
    [JsonObject(MemberSerialization.OptIn)]
    public sealed class TopologyDimensions
    {
        [JsonProperty("widthCells", Required = Required.Always)]
        public int WidthCells { get; set; }

        [JsonProperty("heightCells", Required = Required.Always)]
        public int HeightCells { get; set; }

        [JsonProperty("cellPitchMm", Required = Required.Always)]
        public int CellPitchMm { get; set; }

        [JsonProperty("wallThicknessMm", Required = Required.Always)]
        public int WallThicknessMm { get; set; }

        [JsonProperty("wallHeightMm", Required = Required.Always)]
        public int WallHeightMm { get; set; }
    }

    [Serializable]
    [JsonObject(MemberSerialization.OptIn)]
    public sealed class TopologyPoint
    {
        [JsonProperty("x", Required = Required.Always)]
        public int X { get; set; }

        [JsonProperty("y", Required = Required.Always)]
        public int Y { get; set; }
    }

    [Serializable]
    [JsonObject(MemberSerialization.OptIn)]
    public sealed class TopologyEdge
    {
        public const string VerticalAxis = "vertical";
        public const string HorizontalAxis = "horizontal";

        [JsonProperty("axis", Required = Required.Always)]
        public string Axis { get; set; }

        [JsonProperty("x", Required = Required.Always)]
        public int X { get; set; }

        [JsonProperty("y", Required = Required.Always)]
        public int Y { get; set; }
    }

    [Serializable]
    [JsonObject(MemberSerialization.OptIn)]
    public sealed class TopologyOpening
    {
        [JsonProperty("openingId", Required = Required.Always)]
        public int OpeningId { get; set; }

        [JsonProperty("edge", Required = Required.Always)]
        public TopologyEdge Edge { get; set; }
    }

    [Serializable]
    [JsonObject(MemberSerialization.OptIn)]
    public sealed class TopologyWallState
    {
        [JsonProperty("stateId", Required = Required.Always)]
        public int StateId { get; set; }

        [JsonProperty("edge", Required = Required.Always)]
        public TopologyEdge Edge { get; set; }

        [JsonProperty("quarterTurns", Required = Required.Always)]
        public int QuarterTurns { get; set; }
    }

    [Serializable]
    [JsonObject(MemberSerialization.OptIn)]
    public sealed class TopologyWall
    {
        [JsonProperty("wallId", Required = Required.Always)]
        public int WallId { get; set; }

        /// <summary>Absent/null pour un mur statique, ID explicite pour un bras mobile.</summary>
        [JsonProperty("pivotId", NullValueHandling = NullValueHandling.Include)]
        public int? PivotId { get; set; }

        [JsonProperty("initialStateId", Required = Required.Always)]
        public int InitialStateId { get; set; }

        [JsonProperty("states", Required = Required.Always)]
        public List<TopologyWallState> States { get; set; } = new();
    }

    [Serializable]
    [JsonObject(MemberSerialization.OptIn)]
    public sealed class TopologyPivot
    {
        [JsonProperty("pivotId", Required = Required.Always)]
        public int PivotId { get; set; }

        [JsonProperty("node", Required = Required.Always)]
        public TopologyPoint Node { get; set; }

        [JsonProperty("wallIds", Required = Required.Always)]
        public List<int> WallIds { get; set; } = new();
    }

    [Serializable]
    [JsonObject(MemberSerialization.OptIn)]
    public sealed class TopologySpawn
    {
        [JsonProperty("spawnId", Required = Required.Always)]
        public int SpawnId { get; set; }

        [JsonProperty("cell", Required = Required.Always)]
        public TopologyPoint Cell { get; set; }

        [JsonProperty("yawQuarterTurns", Required = Required.Always)]
        public int YawQuarterTurns { get; set; }
    }
}
