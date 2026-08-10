using System;
using System.Globalization;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

namespace NotThatWay.Game.Topology
{
    /// <summary>
    /// Representation independante de l'indentation et de l'ordre des tableaux.
    /// Les collections portent des IDs stables et sont donc triees par ID avant hash.
    /// </summary>
    public static class TopologyCanonicalizer
    {
        public static byte[] Canonicalize(TopologyDocument document)
        {
            var issues = TopologyValidator.Validate(document);
            if (issues.Count > 0)
                throw new ArgumentException($"Cannot canonicalize invalid topology: {issues[0].Code}.", nameof(document));
            return Encoding.UTF8.GetBytes(ToCanonicalJson(document));
        }

        public static string ComputeChecksum(TopologyDocument document)
        {
            using var algorithm = SHA256.Create();
            var digest = algorithm.ComputeHash(Canonicalize(document));
            var result = new StringBuilder(digest.Length * 2);
            foreach (var value in digest)
                result.Append(value.ToString("x2", CultureInfo.InvariantCulture));
            return result.ToString();
        }

        private static string ToCanonicalJson(TopologyDocument document)
        {
            var builder = new StringBuilder(4096);
            builder.Append("{\"schemaVersion\":");
            AppendInt(builder, document.SchemaVersion);
            builder.Append(",\"topologyId\":\"").Append(document.TopologyId).Append("\",\"dimensions\":{");
            builder.Append("\"widthCells\":");
            AppendInt(builder, document.Dimensions.WidthCells);
            builder.Append(",\"heightCells\":");
            AppendInt(builder, document.Dimensions.HeightCells);
            builder.Append(",\"cellPitchMm\":");
            AppendInt(builder, document.Dimensions.CellPitchMm);
            builder.Append(",\"wallThicknessMm\":");
            AppendInt(builder, document.Dimensions.WallThicknessMm);
            builder.Append(",\"wallHeightMm\":");
            AppendInt(builder, document.Dimensions.WallHeightMm);
            builder.Append("},\"openings\":[");

            var openings = document.Openings.OrderBy(value => value.OpeningId).ToArray();
            for (var index = 0; index < openings.Length; index++)
            {
                if (index > 0)
                    builder.Append(',');
                builder.Append("{\"openingId\":");
                AppendInt(builder, openings[index].OpeningId);
                builder.Append(",\"edge\":");
                AppendEdge(builder, openings[index].Edge);
                builder.Append('}');
            }

            builder.Append("],\"walls\":[");
            var walls = document.Walls.OrderBy(value => value.WallId).ToArray();
            for (var index = 0; index < walls.Length; index++)
            {
                if (index > 0)
                    builder.Append(',');
                var wall = walls[index];
                builder.Append("{\"wallId\":");
                AppendInt(builder, wall.WallId);
                builder.Append(",\"pivotId\":");
                if (wall.PivotId.HasValue)
                    AppendInt(builder, wall.PivotId.Value);
                else
                    builder.Append("null");
                builder.Append(",\"initialStateId\":");
                AppendInt(builder, wall.InitialStateId);
                builder.Append(",\"states\":[");
                var states = wall.States.OrderBy(value => value.StateId).ToArray();
                for (var stateIndex = 0; stateIndex < states.Length; stateIndex++)
                {
                    if (stateIndex > 0)
                        builder.Append(',');
                    var state = states[stateIndex];
                    builder.Append("{\"stateId\":");
                    AppendInt(builder, state.StateId);
                    builder.Append(",\"edge\":");
                    AppendEdge(builder, state.Edge);
                    builder.Append(",\"quarterTurns\":");
                    AppendInt(builder, state.QuarterTurns);
                    builder.Append('}');
                }
                builder.Append("]}");
            }

            builder.Append("],\"pivots\":[");
            var pivots = document.Pivots.OrderBy(value => value.PivotId).ToArray();
            for (var index = 0; index < pivots.Length; index++)
            {
                if (index > 0)
                    builder.Append(',');
                var pivot = pivots[index];
                builder.Append("{\"pivotId\":");
                AppendInt(builder, pivot.PivotId);
                builder.Append(",\"node\":");
                AppendPoint(builder, pivot.Node);
                builder.Append(",\"wallIds\":[");
                var wallIds = pivot.WallIds.OrderBy(value => value).ToArray();
                for (var wallIndex = 0; wallIndex < wallIds.Length; wallIndex++)
                {
                    if (wallIndex > 0)
                        builder.Append(',');
                    AppendInt(builder, wallIds[wallIndex]);
                }
                builder.Append("]}");
            }

            builder.Append("],\"spawns\":[");
            var spawns = document.Spawns.OrderBy(value => value.SpawnId).ToArray();
            for (var index = 0; index < spawns.Length; index++)
            {
                if (index > 0)
                    builder.Append(',');
                var spawn = spawns[index];
                builder.Append("{\"spawnId\":");
                AppendInt(builder, spawn.SpawnId);
                builder.Append(",\"cell\":");
                AppendPoint(builder, spawn.Cell);
                builder.Append(",\"yawQuarterTurns\":");
                AppendInt(builder, spawn.YawQuarterTurns);
                builder.Append('}');
            }
            builder.Append("]}");
            return builder.ToString();
        }

        private static void AppendEdge(StringBuilder builder, TopologyEdge edge)
        {
            builder.Append("{\"axis\":\"").Append(edge.Axis).Append("\",\"x\":");
            AppendInt(builder, edge.X);
            builder.Append(",\"y\":");
            AppendInt(builder, edge.Y);
            builder.Append('}');
        }

        private static void AppendPoint(StringBuilder builder, TopologyPoint point)
        {
            builder.Append("{\"x\":");
            AppendInt(builder, point.X);
            builder.Append(",\"y\":");
            AppendInt(builder, point.Y);
            builder.Append('}');
        }

        private static void AppendInt(StringBuilder builder, int value)
        {
            builder.Append(value.ToString(CultureInfo.InvariantCulture));
        }
    }
}
