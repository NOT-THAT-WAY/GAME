using System.Collections.Generic;

namespace NotThatWay.Game.Topology
{
    public static class TopologyIssueCodes
    {
        public const string JsonInvalid = "json_invalid";
        public const string JsonTooLarge = "json_too_large";
        public const string JsonPropertyDuplicate = "json_property_duplicate";
        public const string JsonMemberUnknown = "json_member_unknown";
        public const string JsonMemberMissing = "json_member_missing";
        public const string JsonTypeInvalid = "json_type_invalid";
        public const string JsonCommentForbidden = "json_comment_forbidden";
        public const string SchemaVersionUnsupported = "schema_version_unsupported";
        public const string TopologyIdInvalid = "topology_id_invalid";
        public const string DimensionsInvalid = "dimensions_invalid";
        public const string OpeningIdDuplicate = "opening_id_duplicate";
        public const string WallIdDuplicate = "wall_id_duplicate";
        public const string PivotIdDuplicate = "pivot_id_duplicate";
        public const string SpawnIdDuplicate = "spawn_id_duplicate";
        public const string StateIdDuplicate = "state_id_duplicate";
        public const string IdInvalid = "id_invalid";
        public const string EdgeOutOfBounds = "edge_out_of_bounds";
        public const string OpeningNotOnPerimeter = "opening_not_on_perimeter";
        public const string SpawnOutOfBounds = "spawn_out_of_bounds";
        public const string PivotOutOfBounds = "pivot_out_of_bounds";
        public const string PivotReferenceMissing = "pivot_reference_missing";
        public const string WallReferenceMissing = "wall_reference_missing";
        public const string PivotWallMissing = "pivot_wall_missing";
        public const string WallPivotMismatch = "wall_pivot_mismatch";
        public const string InitialStateMissing = "initial_state_missing";
        public const string InitialStateRotationInvalid = "initial_state_rotation_invalid";
        public const string QuarterTurnsInvalid = "quarter_turns_invalid";
        public const string QuarterTurnsDuplicate = "quarter_turns_duplicate";
        public const string WallStateEdgeDuplicate = "wall_state_edge_duplicate";
        public const string WallStateRotationMismatch = "wall_state_rotation_mismatch";
        public const string WallStateCountInvalid = "wall_state_count_invalid";
        public const string PivotWallCountInvalid = "pivot_wall_count_invalid";
        public const string WallStateNotIncidentToPivot = "wall_state_not_incident_to_pivot";
        public const string CollectionTooLarge = "collection_too_large";
        public const string InitialEdgeDuplicate = "initial_edge_duplicate";
        public const string OpeningEdgeDuplicate = "opening_edge_duplicate";
        public const string OpeningOverlapsWall = "opening_overlaps_wall";
        public const string ChecksumRequired = "checksum_required";
        public const string ChecksumInvalid = "checksum_invalid";
        public const string ChecksumMismatch = "checksum_mismatch";
    }

    public sealed class TopologyIssue
    {
        public TopologyIssue(string code, string path, string message)
        {
            Code = code;
            Path = path;
            Message = message;
        }

        public string Code { get; }
        public string Path { get; }
        public string Message { get; }
    }

    public sealed class TopologyParseResult
    {
        public TopologyParseResult(TopologyDocument document, IReadOnlyList<TopologyIssue> issues)
        {
            Document = document;
            Issues = issues;
        }

        public TopologyDocument Document { get; }
        public IReadOnlyList<TopologyIssue> Issues { get; }
        public bool IsValid => Document != null && Issues.Count == 0;
    }
}
