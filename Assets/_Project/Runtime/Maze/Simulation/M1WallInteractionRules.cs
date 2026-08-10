using System;
using NotThatWay.Game.Topology;

namespace NotThatWay.Game.Simulation
{
    public enum M1WallInteractionRejection : byte
    {
        None = 0,
        WallMissing = 1,
        WallStatic = 2,
        StateMissing = 3,
        OutOfReach = 4,
        CenterOnWallPlane = 5,
        SweepSideUndetermined = 6,
        StatePairUnsupported = 7
    }

    public readonly struct M1WallInteractionDecision
    {
        private M1WallInteractionDecision(
            bool allowed,
            int effortSign,
            M1WallInteractionRejection rejection)
        {
            Allowed = allowed;
            EffortSign = effortSign;
            Rejection = rejection;
        }

        public bool Allowed { get; }
        public int EffortSign { get; }
        public M1WallInteractionRejection Rejection { get; }

        public static M1WallInteractionDecision Accept(int effortSign)
        {
            if (effortSign != -1 && effortSign != 1)
                throw new ArgumentOutOfRangeException(nameof(effortSign));
            return new M1WallInteractionDecision(true, effortSign, M1WallInteractionRejection.None);
        }

        public static M1WallInteractionDecision Reject(M1WallInteractionRejection rejection)
        {
            if (rejection == M1WallInteractionRejection.None)
                throw new ArgumentOutOfRangeException(nameof(rejection));
            return new M1WallInteractionDecision(false, 0, rejection);
        }
    }

    /// <summary>
    /// Règle de proximité provisoire du banc M1. La cible, la portée et le côté
    /// sont recalculés depuis la pose serveur quantifiée ; le client ne choisit
    /// qu'entre maintenir ou relâcher Interact.
    /// </summary>
    public static class M1WallInteractionRules
    {
        public static M1WallInteractionDecision Evaluate(
            TopologyRuntimeMap map,
            int wallId,
            int stateId,
            int playerCenterXMm,
            int playerCenterZMm,
            int playerRadiusMm,
            int reachFromCapsuleMm)
        {
            if (map == null)
                throw new ArgumentNullException(nameof(map));
            if (playerRadiusMm < 0)
                throw new ArgumentOutOfRangeException(nameof(playerRadiusMm));
            if (reachFromCapsuleMm < 0)
                throw new ArgumentOutOfRangeException(nameof(reachFromCapsuleMm));

            RuntimeWallDefinition wall;
            try
            {
                wall = map.GetWall(wallId);
            }
            catch (ArgumentOutOfRangeException)
            {
                return M1WallInteractionDecision.Reject(M1WallInteractionRejection.WallMissing);
            }

            if (!wall.IsMobile)
                return M1WallInteractionDecision.Reject(M1WallInteractionRejection.WallStatic);
            if (!wall.TryGetState(stateId, out var state))
                return M1WallInteractionDecision.Reject(M1WallInteractionRejection.StateMissing);

            // Le modèle M1 n'admet qu'un aller-retour entre deux poses : c'est ce
            // couple qui définit le sens « le mur s'éloigne du pousseur ».
            if (wall.States.Count != 2)
                return M1WallInteractionDecision.Reject(M1WallInteractionRejection.StatePairUnsupported);
            var negativeStateId = wall.States[0].StateId;
            var positiveStateId = wall.States[1].StateId;
            var destinationStateId = stateId == negativeStateId ? positiveStateId : negativeStateId;

            var box = TopologyGeometry.WallBox(map, wallId, stateId);
            var destinationBox = TopologyGeometry.WallBox(map, wallId, destinationStateId);
            var centerX2 = CheckedTwice(box.CenterMm.X);
            var centerZ2 = CheckedTwice(box.CenterMm.Z);
            var sizeX = CheckedInteger(box.SizeMm.X);
            var sizeZ = CheckedInteger(box.SizeMm.Z);
            var playerX2 = 2L * playerCenterXMm;
            var playerZ2 = 2L * playerCenterZMm;

            var outsideX2 = OutsideDistance(playerX2, centerX2 - sizeX, centerX2 + sizeX);
            var outsideZ2 = OutsideDistance(playerZ2, centerZ2 - sizeZ, centerZ2 + sizeZ);
            var maximumGap2 = 2L * ((long)playerRadiusMm + reachFromCapsuleMm);
            var distanceSquared = (decimal)outsideX2 * outsideX2 +
                                  (decimal)outsideZ2 * outsideZ2;
            if (distanceSquared > (decimal)maximumGap2 * maximumGap2)
                return M1WallInteractionDecision.Reject(M1WallInteractionRejection.OutOfReach);

            var vertical = state.Edge.Axis == TopologyAxis.Vertical;
            var signedSide = vertical ? playerX2 - centerX2 : playerZ2 - centerZ2;
            if (signedSide == 0)
            {
                return M1WallInteractionDecision.Reject(
                    M1WallInteractionRejection.CenterOnWallPlane);
            }

            // Côté vers lequel la pose de destination s'écarte du plan courant :
            // c'est le demi-espace que le mur va balayer.
            var destinationSide = vertical
                ? CheckedTwice(destinationBox.CenterMm.X) - centerX2
                : CheckedTwice(destinationBox.CenterMm.Z) - centerZ2;
            if (destinationSide == 0)
            {
                return M1WallInteractionDecision.Reject(
                    M1WallInteractionRejection.SweepSideUndetermined);
            }

            // Règle de la porte : le mur s'éloigne toujours de celui qui pousse.
            // Depuis le demi-espace opposé à la destination, l'effort va vers
            // cette destination ; depuis l'autre, il retient le mur. Le signe est
            // donc déduit de la géométrie des deux poses, jamais d'un axe figé —
            // sans quoi le trajet retour n'est atteignable que depuis l'arc
            // balayé, c'est-à-dire en se mettant soi-même devant le battant.
            var towardDestination = destinationStateId == positiveStateId ? 1 : -1;
            var pushesAway = signedSide > 0 != destinationSide > 0;
            return M1WallInteractionDecision.Accept(
                pushesAway ? towardDestination : -towardDestination);
        }

        private static long OutsideDistance(long value, long minimum, long maximum)
        {
            if (value < minimum)
                return minimum - value;
            if (value > maximum)
                return value - maximum;
            return 0L;
        }

        private static long CheckedTwice(double value)
        {
            var doubled = value * 2d;
            if (double.IsNaN(doubled) || double.IsInfinity(doubled) ||
                doubled < long.MinValue || doubled > long.MaxValue ||
                Math.Truncate(doubled) != doubled)
            {
                throw new InvalidOperationException("Coordonnée topologique non demi-entière.");
            }
            return (long)doubled;
        }

        private static long CheckedInteger(double value)
        {
            if (double.IsNaN(value) || double.IsInfinity(value) ||
                value < 0d || value > long.MaxValue || Math.Truncate(value) != value)
            {
                throw new InvalidOperationException("Dimension topologique non entière.");
            }
            return (long)value;
        }
    }
}
