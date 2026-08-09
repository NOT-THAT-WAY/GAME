using System;
using System.Collections.Generic;

namespace NotThatWay.Game.Topology
{
    public static class TopologyTransitionRejectionCodes
    {
        public const string None = "none";
        public const string WallMissing = "wall_missing";
        public const string WallStatic = "wall_static";
        public const string StateMissing = "state_missing";
        public const string AlreadyInState = "already_in_state";
        public const string StatesNotAdjacent = "states_not_adjacent";
        public const string DestinationEdgeOccupied = "destination_edge_occupied";
        public const string ConnectivityWouldBreakDuelRegion = "connectivity_would_break_duel_region";
        public const string PerimeterWouldOpen = "perimeter_would_open";
        public const string PlayerInSweptArc = "player_in_swept_arc";
    }

    public readonly struct TopologyTransitionPolicy
    {
        public TopologyTransitionPolicy(
            bool requireSpawnConnectivity,
            bool requireClosedPerimeter,
            bool rejectSweepObstacles)
        {
            RequireSpawnConnectivity = requireSpawnConnectivity;
            RequireClosedPerimeter = requireClosedPerimeter;
            RejectSweepObstacles = rejectSweepObstacles;
        }

        public bool RequireSpawnConnectivity { get; }
        public bool RequireClosedPerimeter { get; }
        public bool RejectSweepObstacles { get; }

        /// <summary>Preset de preuve M1, pas une décision implicite pour la map 16x16.</summary>
        public static TopologyTransitionPolicy GrayboxDuel => new(true, true, true);
    }

    /// <summary>Disque horizontal déjà quantifié dans l'espace local de la topologie.</summary>
    public readonly struct TopologyCircleObstacle
    {
        public TopologyCircleObstacle(int obstacleId, int centerXMm, int centerZMm, int radiusMm)
        {
            if (radiusMm < 0)
                throw new ArgumentOutOfRangeException(nameof(radiusMm));
            ObstacleId = obstacleId;
            CenterXMm = centerXMm;
            CenterZMm = centerZMm;
            RadiusMm = radiusMm;
        }

        public int ObstacleId { get; }
        public int CenterXMm { get; }
        public int CenterZMm { get; }
        public int RadiusMm { get; }
    }

    public readonly struct TopologyTransitionDecision
    {
        private TopologyTransitionDecision(bool allowed, string rejectionCode, int blockingId)
        {
            Allowed = allowed;
            RejectionCode = rejectionCode;
            BlockingId = blockingId;
        }

        public bool Allowed { get; }
        public string RejectionCode { get; }
        public int BlockingId { get; }

        public static TopologyTransitionDecision Accept() =>
            new(true, TopologyTransitionRejectionCodes.None, 0);

        public static TopologyTransitionDecision Reject(string code, int blockingId = 0) =>
            new(false, code, blockingId);
    }

    public static class TopologyTransitionGuard
    {
        public static TopologyTransitionDecision Evaluate(
            TopologyRuntimeMap map,
            IReadOnlyDictionary<int, int> currentStates,
            int wallId,
            int targetStateId,
            TopologyTransitionPolicy policy,
            IReadOnlyList<TopologyCircleObstacle> obstacles)
        {
            if (map == null)
                throw new ArgumentNullException(nameof(map));
            if (currentStates == null)
                throw new ArgumentNullException(nameof(currentStates));
            if (obstacles == null)
                throw new ArgumentNullException(nameof(obstacles));

            RuntimeWallDefinition wall;
            try
            {
                wall = map.GetWall(wallId);
            }
            catch (ArgumentOutOfRangeException)
            {
                return TopologyTransitionDecision.Reject(TopologyTransitionRejectionCodes.WallMissing);
            }
            if (!wall.IsMobile)
                return TopologyTransitionDecision.Reject(TopologyTransitionRejectionCodes.WallStatic);
            if (!wall.TryGetState(targetStateId, out var targetState))
                return TopologyTransitionDecision.Reject(TopologyTransitionRejectionCodes.StateMissing);
            if (!currentStates.TryGetValue(wallId, out var currentStateId) ||
                !wall.TryGetState(currentStateId, out _))
                return TopologyTransitionDecision.Reject(TopologyTransitionRejectionCodes.StateMissing);
            if (currentStateId == targetStateId)
                return TopologyTransitionDecision.Reject(TopologyTransitionRejectionCodes.AlreadyInState);

            TopologySweepSpec sweep;
            try
            {
                sweep = TopologyGeometry.QuarterTurnSweep(map, wallId, currentStateId, targetStateId);
            }
            catch (ArgumentException)
            {
                return TopologyTransitionDecision.Reject(TopologyTransitionRejectionCodes.StatesNotAdjacent);
            }

            foreach (var other in map.Walls)
            {
                if (other.WallId == wallId)
                    continue;
                if (!currentStates.TryGetValue(other.WallId, out var otherStateId) ||
                    !other.TryGetState(otherStateId, out var otherState))
                    return TopologyTransitionDecision.Reject(TopologyTransitionRejectionCodes.StateMissing);
                if (otherState.Edge.Equals(targetState.Edge))
                {
                    return TopologyTransitionDecision.Reject(
                        TopologyTransitionRejectionCodes.DestinationEdgeOccupied,
                        other.WallId);
                }
            }

            var candidateStates = new Dictionary<int, int>(currentStates) { [wallId] = targetStateId };
            if (policy.RequireClosedPerimeter &&
                !TopologyConnectivity.IsPerimeterClosedExceptOpenings(map, candidateStates))
            {
                return TopologyTransitionDecision.Reject(TopologyTransitionRejectionCodes.PerimeterWouldOpen);
            }
            if (policy.RequireSpawnConnectivity &&
                !TopologyConnectivity.AreAllSpawnsConnected(map, candidateStates))
            {
                return TopologyTransitionDecision.Reject(
                    TopologyTransitionRejectionCodes.ConnectivityWouldBreakDuelRegion);
            }
            if (policy.RejectSweepObstacles)
            {
                var hasBlockingObstacle = false;
                var blockingObstacleId = 0;
                foreach (var obstacle in obstacles)
                {
                    if (sweep.IntersectsCircle(
                            obstacle.CenterXMm,
                            obstacle.CenterZMm,
                            obstacle.RadiusMm))
                    {
                        if (!hasBlockingObstacle || obstacle.ObstacleId < blockingObstacleId)
                            blockingObstacleId = obstacle.ObstacleId;
                        hasBlockingObstacle = true;
                    }
                }
                if (hasBlockingObstacle)
                    return TopologyTransitionDecision.Reject(
                        TopologyTransitionRejectionCodes.PlayerInSweptArc,
                        blockingObstacleId);
            }

            return TopologyTransitionDecision.Accept();
        }
    }
}
