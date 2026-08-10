using System;
using System.Collections.Generic;
using System.Linq;

namespace NotThatWay.Game.Topology
{
    public static class TopologyConnectivity
    {
        public static int ShortestPathLength(
            TopologyRuntimeMap map,
            IReadOnlyDictionary<int, int> wallStates,
            TopologyGridCell start,
            TopologyGridCell destination)
        {
            ValidateCell(map, start);
            ValidateCell(map, destination);
            var occupied = BuildOccupiedEdges(map, wallStates);
            var distances = new Dictionary<TopologyGridCell, int> { [start] = 0 };
            var queue = new Queue<TopologyGridCell>();
            queue.Enqueue(start);

            while (queue.Count > 0)
            {
                var cell = queue.Dequeue();
                var distance = distances[cell];
                if (cell.Equals(destination))
                    return distance;

                TryVisit(map, occupied, distances, queue, new TopologyGridCell(cell.X + 1, cell.Y),
                    new TopologyEdgeKey(TopologyAxis.Vertical, cell.X + 1, cell.Y), distance);
                TryVisit(map, occupied, distances, queue, new TopologyGridCell(cell.X - 1, cell.Y),
                    new TopologyEdgeKey(TopologyAxis.Vertical, cell.X, cell.Y), distance);
                TryVisit(map, occupied, distances, queue, new TopologyGridCell(cell.X, cell.Y + 1),
                    new TopologyEdgeKey(TopologyAxis.Horizontal, cell.X, cell.Y + 1), distance);
                TryVisit(map, occupied, distances, queue, new TopologyGridCell(cell.X, cell.Y - 1),
                    new TopologyEdgeKey(TopologyAxis.Horizontal, cell.X, cell.Y), distance);
            }
            return -1;
        }

        public static bool AreAllSpawnsConnected(
            TopologyRuntimeMap map,
            IReadOnlyDictionary<int, int> wallStates)
        {
            if (map.Spawns.Count < 2)
                return true;
            var first = map.Spawns[0].Cell;
            for (var index = 1; index < map.Spawns.Count; index++)
            {
                if (ShortestPathLength(map, wallStates, first, map.Spawns[index].Cell) < 0)
                    return false;
            }
            return true;
        }

        public static bool IsPerimeterClosedExceptOpenings(
            TopologyRuntimeMap map,
            IReadOnlyDictionary<int, int> wallStates)
        {
            var occupied = BuildOccupiedEdges(map, wallStates);
            var openings = new HashSet<TopologyEdgeKey>(map.Openings.Select(value => value.Edge));
            for (var y = 0; y < map.Dimensions.HeightCells; y++)
            {
                if (!IsWallOrOpening(new TopologyEdgeKey(TopologyAxis.Vertical, 0, y), occupied, openings) ||
                    !IsWallOrOpening(
                        new TopologyEdgeKey(TopologyAxis.Vertical, map.Dimensions.WidthCells, y),
                        occupied,
                        openings))
                    return false;
            }
            for (var x = 0; x < map.Dimensions.WidthCells; x++)
            {
                if (!IsWallOrOpening(new TopologyEdgeKey(TopologyAxis.Horizontal, x, 0), occupied, openings) ||
                    !IsWallOrOpening(
                        new TopologyEdgeKey(TopologyAxis.Horizontal, x, map.Dimensions.HeightCells),
                        occupied,
                        openings))
                    return false;
            }
            return true;
        }

        public static HashSet<TopologyEdgeKey> BuildOccupiedEdges(
            TopologyRuntimeMap map,
            IReadOnlyDictionary<int, int> wallStates)
        {
            if (wallStates == null)
                throw new ArgumentNullException(nameof(wallStates));
            var occupied = new HashSet<TopologyEdgeKey>();
            foreach (var wall in map.Walls)
            {
                if (!wallStates.TryGetValue(wall.WallId, out var stateId))
                    throw new ArgumentException($"Etat absent pour le mur {wall.WallId}.", nameof(wallStates));
                var edge = wall.GetState(stateId).Edge;
                if (!occupied.Add(edge))
                    throw new InvalidOperationException($"Deux murs occupent l'arete {edge}.");
            }
            return occupied;
        }

        private static void TryVisit(
            TopologyRuntimeMap map,
            ISet<TopologyEdgeKey> occupied,
            IDictionary<TopologyGridCell, int> distances,
            Queue<TopologyGridCell> queue,
            TopologyGridCell candidate,
            TopologyEdgeKey crossedEdge,
            int distance)
        {
            if (candidate.X < 0 || candidate.X >= map.Dimensions.WidthCells ||
                candidate.Y < 0 || candidate.Y >= map.Dimensions.HeightCells ||
                occupied.Contains(crossedEdge) || distances.ContainsKey(candidate))
                return;
            distances.Add(candidate, distance + 1);
            queue.Enqueue(candidate);
        }

        private static bool IsWallOrOpening(
            TopologyEdgeKey edge,
            ISet<TopologyEdgeKey> occupied,
            ISet<TopologyEdgeKey> openings)
        {
            return occupied.Contains(edge) != openings.Contains(edge);
        }

        private static void ValidateCell(TopologyRuntimeMap map, TopologyGridCell cell)
        {
            if (cell.X < 0 || cell.X >= map.Dimensions.WidthCells ||
                cell.Y < 0 || cell.Y >= map.Dimensions.HeightCells)
            {
                throw new ArgumentOutOfRangeException(nameof(cell), $"Cellule hors grille: {cell}.");
            }
        }
    }
}
