using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

namespace NotThatWay.Game.Topology
{
    public static class TopologyValidator
    {
        private const int MaximumGridSide = 1024;
        private const int MaximumWallStates = 4;
        private const int MaximumWallsPerPivot = 4;

        private static readonly Regex TopologyIdPattern =
            new Regex("^[a-z0-9]+(?:-[a-z0-9]+)*$", RegexOptions.CultureInvariant);

        public static IReadOnlyList<TopologyIssue> Validate(TopologyDocument document)
        {
            var issues = new List<TopologyIssue>();
            if (document == null)
            {
                Add(issues, TopologyIssueCodes.JsonTypeInvalid, "$", "Le document est null.");
                return issues;
            }

            if (document.SchemaVersion != 1)
            {
                Add(
                    issues,
                    TopologyIssueCodes.SchemaVersionUnsupported,
                    "$.schemaVersion",
                    $"Version {document.SchemaVersion} non supportee; version attendue: 1.");
            }

            if (document.TopologyId == null || !TopologyIdPattern.IsMatch(document.TopologyId))
                Add(issues, TopologyIssueCodes.TopologyIdInvalid, "$.topologyId", "Slug de topologie invalide.");

            if (!ValidateDimensions(document.Dimensions, issues))
                return issues;

            if (document.Openings == null || document.Walls == null || document.Pivots == null || document.Spawns == null)
            {
                Add(issues, TopologyIssueCodes.JsonTypeInvalid, "$", "Les collections de topologie ne peuvent pas etre null.");
                return issues;
            }

            ValidateUniqueIds(document.Openings, item => item?.OpeningId ?? 0, TopologyIssueCodes.OpeningIdDuplicate,
                "$.openings", issues);
            ValidateUniqueIds(document.Walls, item => item?.WallId ?? 0, TopologyIssueCodes.WallIdDuplicate,
                "$.walls", issues);
            ValidateUniqueIds(document.Pivots, item => item?.PivotId ?? 0, TopologyIssueCodes.PivotIdDuplicate,
                "$.pivots", issues);
            ValidateUniqueIds(document.Spawns, item => item?.SpawnId ?? 0, TopologyIssueCodes.SpawnIdDuplicate,
                "$.spawns", issues);

            var pivotsById = FirstByPositiveId(document.Pivots, pivot => pivot?.PivotId ?? 0);
            var wallsById = FirstByPositiveId(document.Walls, wall => wall?.WallId ?? 0);

            ValidateCardinality(document, issues);
            ValidateOpenings(document, issues);
            ValidatePivots(document, wallsById, pivotsById, issues);
            ValidateWalls(document, pivotsById, issues);
            ValidateSpawns(document, issues);
            ValidateOccupiedEdges(document, issues);
            return issues;
        }

        public static IReadOnlyList<TopologyIssue> ValidateForRuntime(TopologyDocument document)
        {
            var issues = new List<TopologyIssue>(Validate(document));
            if (issues.Count > 0)
                return issues;

            for (var index = 0; index < document.Pivots.Count; index++)
            {
                if (document.Pivots[index].WallIds.Count == 0)
                {
                    Add(
                        issues,
                        TopologyIssueCodes.PivotWallCountInvalid,
                        $"$.pivots[{index}].wallIds",
                        "Un pivot runtime doit porter au moins un mur.");
                }
            }

            for (var index = 0; index < document.Walls.Count; index++)
            {
                var wall = document.Walls[index];
                if (wall.PivotId.HasValue && wall.States.Count < 2)
                {
                    Add(
                        issues,
                        TopologyIssueCodes.WallStateCountInvalid,
                        $"$.walls[{index}].states",
                        "Un mur mobile runtime doit exposer au moins deux poses distinctes.");
                }
            }

            return issues;
        }

        private static void ValidateCardinality(TopologyDocument document, ICollection<TopologyIssue> issues)
        {
            var width = (long)document.Dimensions.WidthCells;
            var height = (long)document.Dimensions.HeightCells;
            var maximumEdges = 2L * width * height + width + height;
            var maximumPerimeterEdges = 2L * width + 2L * height;
            var maximumNodes = (width + 1L) * (height + 1L);
            var maximumCells = width * height;

            ValidateMaximum(document.Openings.Count, maximumPerimeterEdges, "$.openings", issues);
            ValidateMaximum(document.Walls.Count, maximumEdges, "$.walls", issues);
            ValidateMaximum(document.Pivots.Count, maximumNodes, "$.pivots", issues);
            ValidateMaximum(document.Spawns.Count, maximumCells, "$.spawns", issues);
        }

        private static bool ValidateDimensions(TopologyDimensions dimensions, ICollection<TopologyIssue> issues)
        {
            if (dimensions == null)
            {
                Add(issues, TopologyIssueCodes.DimensionsInvalid, "$.dimensions", "Dimensions absentes.");
                return false;
            }

            var valid = dimensions.WidthCells is >= 1 and <= MaximumGridSide &&
                        dimensions.HeightCells is >= 1 and <= MaximumGridSide &&
                        dimensions.CellPitchMm > 0 &&
                        dimensions.WallThicknessMm > 0 &&
                        dimensions.WallThicknessMm < dimensions.CellPitchMm &&
                        dimensions.WallHeightMm > 0;
            if (!valid)
                Add(issues, TopologyIssueCodes.DimensionsInvalid, "$.dimensions", "Dimensions hors contrat.");
            return valid;
        }

        private static void ValidateOpenings(TopologyDocument document, ICollection<TopologyIssue> issues)
        {
            for (var index = 0; index < document.Openings.Count; index++)
            {
                var opening = document.Openings[index];
                var path = $"$.openings[{index}]";
                if (opening == null)
                {
                    Add(issues, TopologyIssueCodes.JsonTypeInvalid, path, "Ouverture null.");
                    continue;
                }
                ValidatePositiveId(opening.OpeningId, path + ".openingId", issues);
                if (!ValidateEdge(opening.Edge, document.Dimensions, path + ".edge", issues))
                    continue;
                if (!IsPerimeter(opening.Edge, document.Dimensions))
                {
                    Add(
                        issues,
                        TopologyIssueCodes.OpeningNotOnPerimeter,
                        path + ".edge",
                        "Une ouverture doit etre portee par le perimetre.");
                }
            }
        }

        private static void ValidatePivots(
            TopologyDocument document,
            IReadOnlyDictionary<int, TopologyWall> wallsById,
            IReadOnlyDictionary<int, TopologyPivot> pivotsById,
            ICollection<TopologyIssue> issues)
        {
            for (var index = 0; index < document.Pivots.Count; index++)
            {
                var pivot = document.Pivots[index];
                var path = $"$.pivots[{index}]";
                if (pivot == null || pivot.Node == null || pivot.WallIds == null)
                {
                    Add(issues, TopologyIssueCodes.JsonTypeInvalid, path, "Pivot incomplet.");
                    continue;
                }
                ValidatePositiveId(pivot.PivotId, path + ".pivotId", issues);
                if (pivot.Node.X < 0 || pivot.Node.X > document.Dimensions.WidthCells ||
                    pivot.Node.Y < 0 || pivot.Node.Y > document.Dimensions.HeightCells)
                {
                    Add(issues, TopologyIssueCodes.PivotOutOfBounds, path + ".node", "Noeud de pivot hors grille.");
                }

                if (pivot.WallIds.Count > MaximumWallsPerPivot)
                {
                    Add(
                        issues,
                        TopologyIssueCodes.PivotWallCountInvalid,
                        path + ".wallIds",
                        $"Un pivot ne peut porter plus de {MaximumWallsPerPivot} murs.");
                }

                var uniqueWallIds = new HashSet<int>();
                foreach (var wallId in pivot.WallIds)
                {
                    ValidatePositiveId(wallId, path + ".wallIds", issues);
                    if (!uniqueWallIds.Add(wallId) || !wallsById.TryGetValue(wallId, out var wall))
                    {
                        Add(
                            issues,
                            TopologyIssueCodes.WallReferenceMissing,
                            path + ".wallIds",
                            $"Mur {wallId} absent ou reference plusieurs fois.");
                        continue;
                    }

                    // Si le mur vise un pivot absent, ValidateWalls porte l'erreur
                    // causale. Ne pas ajouter ici un symptome reciproque trompeur.
                    if (!wall.PivotId.HasValue ||
                        wall.PivotId.Value != pivot.PivotId && pivotsById.ContainsKey(wall.PivotId.Value))
                    {
                        Add(
                            issues,
                            TopologyIssueCodes.WallPivotMismatch,
                            path + ".wallIds",
                            $"Le mur {wallId} ne declare pas le pivot {pivot.PivotId}.");
                    }
                }
            }
        }

        private static void ValidateWalls(
            TopologyDocument document,
            IReadOnlyDictionary<int, TopologyPivot> pivotsById,
            ICollection<TopologyIssue> issues)
        {
            for (var index = 0; index < document.Walls.Count; index++)
            {
                var wall = document.Walls[index];
                var path = $"$.walls[{index}]";
                if (wall == null || wall.States == null)
                {
                    Add(issues, TopologyIssueCodes.JsonTypeInvalid, path, "Mur incomplet.");
                    continue;
                }
                ValidatePositiveId(wall.WallId, path + ".wallId", issues);
                ValidateNonNegativeId(wall.InitialStateId, path + ".initialStateId", issues);

                if (wall.States.Count == 0 || wall.States.Count > MaximumWallStates)
                {
                    Add(
                        issues,
                        TopologyIssueCodes.WallStateCountInvalid,
                        path + ".states",
                        $"Un mur doit declarer entre 1 et {MaximumWallStates} etats.");
                }
                if (!wall.PivotId.HasValue && wall.States.Count != 1)
                {
                    Add(
                        issues,
                        TopologyIssueCodes.WallStateCountInvalid,
                        path + ".states",
                        "Un mur statique doit declarer exactement un etat.");
                }

                TopologyPivot pivot = null;
                if (wall.PivotId.HasValue)
                {
                    ValidatePositiveId(wall.PivotId.Value, path + ".pivotId", issues);
                    if (!pivotsById.TryGetValue(wall.PivotId.Value, out pivot))
                    {
                        Add(
                            issues,
                            TopologyIssueCodes.PivotReferenceMissing,
                            path + ".pivotId",
                            $"Pivot {wall.PivotId.Value} absent.");
                    }
                    else if (!pivot.WallIds.Contains(wall.WallId))
                    {
                        Add(
                            issues,
                            TopologyIssueCodes.PivotWallMissing,
                            path + ".pivotId",
                            $"Le pivot {pivot.PivotId} ne porte pas le mur {wall.WallId}.");
                    }
                }

                var stateIds = new HashSet<int>();
                var stateEdges = new HashSet<string>(StringComparer.Ordinal);
                var quarterTurns = new HashSet<int>();
                var initialStateFound = false;
                TopologyWallState initialState = null;
                for (var stateIndex = 0; stateIndex < wall.States.Count; stateIndex++)
                {
                    var state = wall.States[stateIndex];
                    var statePath = path + $".states[{stateIndex}]";
                    if (state == null)
                    {
                        Add(issues, TopologyIssueCodes.JsonTypeInvalid, statePath, "Etat de mur null.");
                        continue;
                    }
                    if (!stateIds.Add(state.StateId))
                        Add(issues, TopologyIssueCodes.StateIdDuplicate, statePath + ".stateId", "ID d'etat duplique.");
                    ValidateNonNegativeId(state.StateId, statePath + ".stateId", issues);
                    if (state.StateId == wall.InitialStateId)
                    {
                        initialStateFound = true;
                        initialState ??= state;
                    }
                    if (state.QuarterTurns is < 0 or > 3)
                    {
                        Add(
                            issues,
                            TopologyIssueCodes.QuarterTurnsInvalid,
                            statePath + ".quarterTurns",
                            "Un quart de tour canonique vaut 0, 1, 2 ou 3.");
                    }
                    else if (!quarterTurns.Add(state.QuarterTurns))
                    {
                        Add(
                            issues,
                            TopologyIssueCodes.QuarterTurnsDuplicate,
                            statePath + ".quarterTurns",
                            "Deux poses du meme mur ne peuvent pas partager le meme quart de tour.");
                    }

                    if (!ValidateEdge(state.Edge, document.Dimensions, statePath + ".edge", issues))
                        continue;
                    if (!stateEdges.Add(EdgeKey(state.Edge)))
                    {
                        Add(
                            issues,
                            TopologyIssueCodes.WallStateEdgeDuplicate,
                            statePath + ".edge",
                            "Deux etats du meme mur ne peuvent pas occuper la meme arete.");
                    }
                    if (pivot?.Node != null && !Touches(state.Edge, pivot.Node))
                    {
                        Add(
                            issues,
                            TopologyIssueCodes.WallStateNotIncidentToPivot,
                            statePath + ".edge",
                            "Chaque pose mobile doit toucher son pivot.");
                    }
                }

                if (!initialStateFound)
                {
                    Add(
                        issues,
                        TopologyIssueCodes.InitialStateMissing,
                        path + ".initialStateId",
                        $"Etat initial {wall.InitialStateId} absent.");
                }

                if (initialState == null)
                    continue;
                if (initialState.QuarterTurns != 0)
                {
                    Add(
                        issues,
                        TopologyIssueCodes.InitialStateRotationInvalid,
                        path + ".initialStateId",
                        "L'etat initial doit etre la rotation canonique 0.");
                }

                if (pivot?.Node == null ||
                    !TryDirection(initialState.Edge, pivot.Node, out var initialDirection))
                    continue;

                for (var stateIndex = 0; stateIndex < wall.States.Count; stateIndex++)
                {
                    var state = wall.States[stateIndex];
                    if (state == null || state.QuarterTurns is < 0 or > 3 ||
                        !TryDirection(state.Edge, pivot.Node, out var direction))
                        continue;
                    if (direction != (initialDirection + state.QuarterTurns) % 4)
                    {
                        Add(
                            issues,
                            TopologyIssueCodes.WallStateRotationMismatch,
                            path + $".states[{stateIndex}]",
                            "L'arete ne correspond pas a la rotation declaree depuis l'etat initial.");
                    }
                }
            }
        }

        private static void ValidateOccupiedEdges(TopologyDocument document, ICollection<TopologyIssue> issues)
        {
            var initialWalls = new Dictionary<string, int>(StringComparer.Ordinal);
            var seenWallIds = new HashSet<int>();
            for (var index = 0; index < document.Walls.Count; index++)
            {
                var wall = document.Walls[index];
                if (wall?.States == null || !seenWallIds.Add(wall.WallId))
                    continue;
                var initial = wall.States.FirstOrDefault(state => state?.StateId == wall.InitialStateId);
                if (initial == null || !IsValidEdge(initial.Edge, document.Dimensions))
                    continue;
                var key = EdgeKey(initial.Edge);
                if (initialWalls.TryGetValue(key, out var existingWallId))
                {
                    Add(
                        issues,
                        TopologyIssueCodes.InitialEdgeDuplicate,
                        $"$.walls[{index}].initialStateId",
                        $"Les murs {existingWallId} et {wall.WallId} occupent la meme arete initiale.");
                }
                else
                {
                    initialWalls.Add(key, wall.WallId);
                }
            }

            var openingEdges = new HashSet<string>(StringComparer.Ordinal);
            for (var index = 0; index < document.Openings.Count; index++)
            {
                var opening = document.Openings[index];
                if (opening == null || !IsValidEdge(opening.Edge, document.Dimensions))
                    continue;
                var key = EdgeKey(opening.Edge);
                if (!openingEdges.Add(key))
                {
                    Add(
                        issues,
                        TopologyIssueCodes.OpeningEdgeDuplicate,
                        $"$.openings[{index}].edge",
                        "Deux ouvertures declarent la meme arete.");
                }
                if (initialWalls.ContainsKey(key))
                {
                    Add(
                        issues,
                        TopologyIssueCodes.OpeningOverlapsWall,
                        $"$.openings[{index}].edge",
                        "Une ouverture ne peut pas etre occupee par un mur initial.");
                }
            }
        }

        private static void ValidateSpawns(TopologyDocument document, ICollection<TopologyIssue> issues)
        {
            for (var index = 0; index < document.Spawns.Count; index++)
            {
                var spawn = document.Spawns[index];
                var path = $"$.spawns[{index}]";
                if (spawn == null || spawn.Cell == null)
                {
                    Add(issues, TopologyIssueCodes.JsonTypeInvalid, path, "Spawn incomplet.");
                    continue;
                }
                ValidatePositiveId(spawn.SpawnId, path + ".spawnId", issues);
                if (spawn.Cell.X < 0 || spawn.Cell.X >= document.Dimensions.WidthCells ||
                    spawn.Cell.Y < 0 || spawn.Cell.Y >= document.Dimensions.HeightCells)
                {
                    Add(issues, TopologyIssueCodes.SpawnOutOfBounds, path + ".cell", "Spawn hors grille.");
                }
                if (spawn.YawQuarterTurns is < 0 or > 3)
                {
                    Add(
                        issues,
                        TopologyIssueCodes.QuarterTurnsInvalid,
                        path + ".yawQuarterTurns",
                        "Orientation de spawn invalide.");
                }
            }
        }

        private static bool ValidateEdge(
            TopologyEdge edge,
            TopologyDimensions dimensions,
            string path,
            ICollection<TopologyIssue> issues)
        {
            var valid = IsValidEdge(edge, dimensions);
            if (!valid)
                Add(issues, TopologyIssueCodes.EdgeOutOfBounds, path, "Arête ou axe hors grille.");
            return valid;
        }

        private static bool IsValidEdge(TopologyEdge edge, TopologyDimensions dimensions)
        {
            return edge != null && (edge.Axis == TopologyEdge.VerticalAxis
                ? edge.X >= 0 && edge.X <= dimensions.WidthCells && edge.Y >= 0 && edge.Y < dimensions.HeightCells
                : edge.Axis == TopologyEdge.HorizontalAxis && edge.X >= 0 && edge.X < dimensions.WidthCells &&
                  edge.Y >= 0 && edge.Y <= dimensions.HeightCells);
        }

        private static bool IsPerimeter(TopologyEdge edge, TopologyDimensions dimensions)
        {
            return edge.Axis == TopologyEdge.VerticalAxis
                ? edge.X == 0 || edge.X == dimensions.WidthCells
                : edge.Y == 0 || edge.Y == dimensions.HeightCells;
        }

        private static bool Touches(TopologyEdge edge, TopologyPoint node)
        {
            return edge.Axis == TopologyEdge.VerticalAxis
                ? edge.X == node.X && (edge.Y == node.Y || edge.Y + 1 == node.Y)
                : edge.Y == node.Y && (edge.X == node.X || edge.X + 1 == node.X);
        }

        private static bool TryDirection(TopologyEdge edge, TopologyPoint node, out int direction)
        {
            direction = 0;
            if (edge == null || node == null)
                return false;
            if (edge.Axis == TopologyEdge.VerticalAxis && edge.X == node.X)
            {
                if (edge.Y == node.Y)
                {
                    direction = 0; // N
                    return true;
                }
                if (edge.Y + 1 == node.Y)
                {
                    direction = 2; // S
                    return true;
                }
            }
            else if (edge.Axis == TopologyEdge.HorizontalAxis && edge.Y == node.Y)
            {
                if (edge.X == node.X)
                {
                    direction = 1; // E
                    return true;
                }
                if (edge.X + 1 == node.X)
                {
                    direction = 3; // W
                    return true;
                }
            }
            return false;
        }

        private static string EdgeKey(TopologyEdge edge)
        {
            return $"{edge.Axis}:{edge.X}:{edge.Y}";
        }

        private static void ValidateMaximum(
            int count,
            long maximum,
            string path,
            ICollection<TopologyIssue> issues)
        {
            if (count > maximum)
            {
                Add(
                    issues,
                    TopologyIssueCodes.CollectionTooLarge,
                    path,
                    $"La collection contient {count} elements; maximum pour cette grille: {maximum}.");
            }
        }

        private static Dictionary<int, T> FirstByPositiveId<T>(IEnumerable<T> values, Func<T, int> getId)
        {
            var result = new Dictionary<int, T>();
            foreach (var value in values)
            {
                var id = getId(value);
                if (id > 0 && !result.ContainsKey(id))
                    result.Add(id, value);
            }
            return result;
        }

        private static void ValidateUniqueIds<T>(
            IEnumerable<T> values,
            Func<T, int> getId,
            string duplicateCode,
            string path,
            ICollection<TopologyIssue> issues)
        {
            var ids = new HashSet<int>();
            foreach (var value in values)
            {
                var id = getId(value);
                if (id > 0 && !ids.Add(id))
                    Add(issues, duplicateCode, path, $"ID {id} duplique.");
            }
        }

        private static void ValidatePositiveId(int id, string path, ICollection<TopologyIssue> issues)
        {
            if (id <= 0)
                Add(issues, TopologyIssueCodes.IdInvalid, path, "Un ID stable doit etre strictement positif.");
        }

        private static void ValidateNonNegativeId(int id, string path, ICollection<TopologyIssue> issues)
        {
            if (id < 0)
                Add(issues, TopologyIssueCodes.IdInvalid, path, "Un ID d'etat doit etre positif ou nul.");
        }

        private static void Add(ICollection<TopologyIssue> issues, string code, string path, string message)
        {
            issues.Add(new TopologyIssue(code, path, message));
        }
    }
}
