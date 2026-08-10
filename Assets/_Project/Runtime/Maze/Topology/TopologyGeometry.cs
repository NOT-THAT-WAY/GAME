using System;
using NotThatWay.Game.Simulation;
using UnityEngine;

namespace NotThatWay.Game.Topology
{
    public readonly struct TopologyPointMm
    {
        public TopologyPointMm(double x, double y, double z)
        {
            X = x;
            Y = y;
            Z = z;
        }

        public double X { get; }
        public double Y { get; }
        public double Z { get; }
        public Vector3 Meters => new((float)(X / 1000d), (float)(Y / 1000d), (float)(Z / 1000d));
    }

    public readonly struct TopologyWallBoxSpec
    {
        public TopologyWallBoxSpec(
            int wallId,
            int stateId,
            TopologyEdgeKey edge,
            TopologyPointMm centerMm,
            TopologyPointMm sizeMm)
        {
            WallId = wallId;
            StateId = stateId;
            Edge = edge;
            CenterMm = centerMm;
            SizeMm = sizeMm;
        }

        public int WallId { get; }
        public int StateId { get; }
        public TopologyEdgeKey Edge { get; }
        public TopologyPointMm CenterMm { get; }
        public TopologyPointMm SizeMm { get; }
        public Vector3 CenterMeters => CenterMm.Meters;
        public Vector3 SizeMeters => SizeMm.Meters;

        /// <summary>
        /// Test horizontal exact d'un disque contre la pose, en coordonnées
        /// doublées : le même verdict sous Mono et sous Windows IL2CPP, tangences
        /// comprises.
        /// </summary>
        public bool IntersectsCircle(int centerXMm, int centerZMm, int radiusMm)
        {
            if (radiusMm < 0)
                throw new ArgumentOutOfRangeException(nameof(radiusMm));

            var boxX2 = Doubled(CenterMm.X);
            var boxZ2 = Doubled(CenterMm.Z);
            var sizeX = Whole(SizeMm.X);
            var sizeZ = Whole(SizeMm.Z);
            var outsideX2 = OutsideDistance(2L * centerXMm, boxX2 - sizeX, boxX2 + sizeX);
            var outsideZ2 = OutsideDistance(2L * centerZMm, boxZ2 - sizeZ, boxZ2 + sizeZ);
            var radius2 = 2L * radiusMm;
            return (decimal)outsideX2 * outsideX2 + (decimal)outsideZ2 * outsideZ2 <=
                   (decimal)radius2 * radius2;
        }

        private static long OutsideDistance(long value, long minimum, long maximum)
        {
            if (value < minimum)
                return minimum - value;
            return value > maximum ? value - maximum : 0L;
        }

        private static long Doubled(double value)
        {
            var doubled = value * 2d;
            if (double.IsNaN(doubled) || double.IsInfinity(doubled) ||
                Math.Truncate(doubled) != doubled)
            {
                throw new InvalidOperationException("Coordonnée topologique non demi-entière.");
            }
            return (long)doubled;
        }

        private static long Whole(double value)
        {
            if (double.IsNaN(value) || double.IsInfinity(value) || value < 0d ||
                Math.Truncate(value) != value)
            {
                throw new InvalidOperationException("Dimension topologique non entière.");
            }
            return (long)value;
        }
    }

    public readonly struct TopologySweepSpec
    {
        private readonly long _pivotX2Mm;
        private readonly long _pivotZ2Mm;

        internal TopologySweepSpec(
            int wallId,
            long pivotX2Mm,
            long pivotZ2Mm,
            int fromDirection,
            int signedQuarterTurn,
            int lengthMm,
            int thicknessMm)
        {
            WallId = wallId;
            _pivotX2Mm = pivotX2Mm;
            _pivotZ2Mm = pivotZ2Mm;
            FromDirection = fromDirection;
            SignedQuarterTurn = signedQuarterTurn;
            LengthMm = lengthMm;
            ThicknessMm = thicknessMm;
        }

        public int WallId { get; }
        public TopologyPointMm PivotMm => new(_pivotX2Mm / 2d, 0d, _pivotZ2Mm / 2d);
        public int FromDirection { get; }
        public int SignedQuarterTurn { get; }
        public int LengthMm { get; }
        public int ThicknessMm { get; }

        /// <summary>
        /// Test horizontal conservateur d'un disque contre le quart de disque balayé.
        /// Tout le prédicat est entier (coordonnées doublées) : aucune tangence ne
        /// dépend des implémentations flottantes de Mono ou d'IL2CPP.
        /// </summary>
        public bool IntersectsCircle(int centerXMm, int centerZMm, int radiusMm)
        {
            if (radiusMm < 0)
                throw new ArgumentOutOfRangeException(nameof(radiusMm));

            var dx2 = 2L * centerXMm - _pivotX2Mm;
            var dz2 = 2L * centerZMm - _pivotZ2Mm;
            var padding2 = ThicknessMm + 2L * radiusMm;
            var outerRadius2 = 2L * LengthMm + padding2;

            // decimal évite tout overflow du carré, y compris pour des centres
            // d'obstacle proches des bornes d'un int signé.
            var distanceSquared = (decimal)dx2 * dx2 + (decimal)dz2 * dz2;
            var outerSquared = (decimal)outerRadius2 * outerRadius2;
            if (distanceSquared > outerSquared)
                return false;

            long forward;
            long positiveTurn;
            switch (FromDirection)
            {
                case 0: // nord -> est
                    forward = dz2;
                    positiveTurn = dx2;
                    break;
                case 1: // est -> sud
                    forward = dx2;
                    positiveTurn = -dz2;
                    break;
                case 2: // sud -> ouest
                    forward = -dz2;
                    positiveTurn = -dx2;
                    break;
                case 3: // ouest -> nord
                    forward = -dx2;
                    positiveTurn = dz2;
                    break;
                default:
                    throw new InvalidOperationException($"Direction canonique invalide: {FromDirection}.");
            }

            var towardTarget = SignedQuarterTurn > 0 ? positiveTurn : -positiveTurn;
            return forward >= -padding2 && towardTarget >= -padding2;
        }
    }

    /// <summary>
    /// Mesure entière d'un contact entre un disque et le battant à un angle
    /// quelconque. Aucune décision n'est prise ici : la règle de jeu lit ces trois
    /// nombres et en déduit portée, sens et puissance.
    /// </summary>
    public readonly struct TopologyBladeContact
    {
        internal TopologyBladeContact(bool withinReach, int lateralSign, int contactPermille)
        {
            WithinReach = withinReach;
            LateralSign = lateralSign;
            ContactPermille = contactPermille;
        }

        /// <summary>Le disque touche le battant, gond et bout compris.</summary>
        public bool WithinReach { get; }

        /// <summary>
        /// Côté occupé par le disque : +1 du côté vers lequel une rotation positive
        /// emmène le battant, -1 de l'autre, 0 exactement dans son plan.
        /// </summary>
        public int LateralSign { get; }

        /// <summary>Abscisse du contact, 0 au gond et 1000 au bout du battant.</summary>
        public int ContactPermille { get; }
    }

    /// <summary>
    /// Battant libre vu comme un segment issu de son gond. L'angle est en
    /// milli-degrés et la trigonométrie est entière : le même verdict de contact
    /// sous Mono et sous Windows IL2CPP, quel que soit l'angle.
    /// </summary>
    public readonly struct TopologyBladeSpec
    {
        /// <summary>Échelle de l'abscisse de contact, alignée sur le pour-mille du couple.</summary>
        public const int ContactScale = WallSimulationSettings.PermilleScale;

        private readonly long _pivotX2Mm;
        private readonly long _pivotZ2Mm;
        private readonly int _baseDirection;

        internal TopologyBladeSpec(
            int wallId,
            long pivotX2Mm,
            long pivotZ2Mm,
            int baseDirection,
            int lengthMm,
            int thicknessMm)
        {
            WallId = wallId;
            _pivotX2Mm = pivotX2Mm;
            _pivotZ2Mm = pivotZ2Mm;
            _baseDirection = baseDirection;
            LengthMm = lengthMm;
            ThicknessMm = thicknessMm;
        }

        public int WallId { get; }
        public TopologyPointMm PivotMm => new(_pivotX2Mm / 2d, 0d, _pivotZ2Mm / 2d);
        public int LengthMm { get; }
        public int ThicknessMm { get; }

        /// <summary>Direction canonique du battant à l'angle zéro (0=N, 1=E, 2=S, 3=O).</summary>
        public int BaseDirection => _baseDirection;

        /// <summary>Direction unitaire du battant en Q16, gond vers bout.</summary>
        public void UnitDirection(int angleMilliDegrees, out int unitXQ16, out int unitZQ16)
        {
            FixedTrigonometry.SinCos(angleMilliDegrees, out var sin, out var cos);
            CardinalDirection(_baseDirection, out var baseX, out var baseZ);
            unitXQ16 = baseX * cos + baseZ * sin;
            unitZQ16 = -baseX * sin + baseZ * cos;
        }

        public TopologyBladeContact Probe(
            int angleMilliDegrees,
            int centerXMm,
            int centerZMm,
            int radiusMm,
            int reachMm)
        {
            if (radiusMm < 0)
                throw new ArgumentOutOfRangeException(nameof(radiusMm));
            if (reachMm < 0)
                throw new ArgumentOutOfRangeException(nameof(reachMm));

            UnitDirection(angleMilliDegrees, out var unitX, out var unitZ);
            var dx2 = 2L * centerXMm - _pivotX2Mm;
            var dz2 = 2L * centerZMm - _pivotZ2Mm;
            var alongQ16 = dx2 * unitX + dz2 * unitZ;
            var lateralQ16 = unitZ * dx2 - unitX * dz2;

            var maximumAlongQ16 = 2L * LengthMm * FixedTrigonometry.Scale;
            var clampedAlongQ16 = alongQ16 < 0L
                ? 0L
                : alongQ16 > maximumAlongQ16
                    ? maximumAlongQ16
                    : alongQ16;
            var overshootQ16 = alongQ16 - clampedAlongQ16;

            // Épaisseur déjà doublée : la demi-épaisseur en unités doublées vaut
            // exactement ThicknessMm, sans division ni arrondi.
            var padding2 = ThicknessMm + 2L * ((long)radiusMm + reachMm);
            var paddingQ16 = padding2 * FixedTrigonometry.Scale;
            var distanceSquared = (decimal)overshootQ16 * overshootQ16 +
                                  (decimal)lateralQ16 * lateralQ16;
            var withinReach = distanceSquared <= (decimal)paddingQ16 * paddingQ16;

            var contactPermille = (int)(ContactScale * clampedAlongQ16 / maximumAlongQ16);
            return new TopologyBladeContact(
                withinReach,
                lateralQ16 > 0L ? 1 : lateralQ16 < 0L ? -1 : 0,
                contactPermille);
        }

        private static void CardinalDirection(int direction, out int x, out int z)
        {
            switch (direction)
            {
                case 0:
                    x = 0;
                    z = 1;
                    return;
                case 1:
                    x = 1;
                    z = 0;
                    return;
                case 2:
                    x = 0;
                    z = -1;
                    return;
                case 3:
                    x = -1;
                    z = 0;
                    return;
                default:
                    throw new InvalidOperationException($"Direction canonique invalide: {direction}.");
            }
        }
    }

    /// <summary>Conversion canonique grille (+X,+Y) vers monde Unity (+X,+Z).</summary>
    public static class TopologyGeometry
    {
        public static TopologyPointMm CellCenterMm(TopologyRuntimeMap map, TopologyGridCell cell)
        {
            ValidateCell(map, cell);
            var pitch = map.Dimensions.CellPitchMm;
            return new TopologyPointMm(
                (cell.X + 0.5d - map.Dimensions.WidthCells * 0.5d) * pitch,
                0d,
                (cell.Y + 0.5d - map.Dimensions.HeightCells * 0.5d) * pitch);
        }

        public static TopologyPointMm NodeMm(TopologyRuntimeMap map, int x, int y)
        {
            if (x < 0 || x > map.Dimensions.WidthCells || y < 0 || y > map.Dimensions.HeightCells)
                throw new ArgumentOutOfRangeException(nameof(x), $"Noeud hors grille: {x},{y}.");
            var pitch = map.Dimensions.CellPitchMm;
            return new TopologyPointMm(
                (x - map.Dimensions.WidthCells * 0.5d) * pitch,
                0d,
                (y - map.Dimensions.HeightCells * 0.5d) * pitch);
        }

        public static TopologyWallBoxSpec WallBox(TopologyRuntimeMap map, int wallId, int stateId)
        {
            var wall = map.GetWall(wallId);
            var state = wall.GetState(stateId);
            var dimensions = map.Dimensions;
            var pitch = dimensions.CellPitchMm;
            var centerX = (state.Edge.X - dimensions.WidthCells * 0.5d) * pitch;
            var centerZ = (state.Edge.Y - dimensions.HeightCells * 0.5d) * pitch;
            TopologyPointMm size;
            if (state.Edge.Axis == TopologyAxis.Vertical)
            {
                centerZ += pitch * 0.5d;
                size = new TopologyPointMm(dimensions.WallThicknessMm, dimensions.WallHeightMm, pitch);
            }
            else
            {
                centerX += pitch * 0.5d;
                size = new TopologyPointMm(pitch, dimensions.WallHeightMm, dimensions.WallThicknessMm);
            }

            return new TopologyWallBoxSpec(
                wallId,
                stateId,
                state.Edge,
                new TopologyPointMm(centerX, dimensions.WallHeightMm * 0.5d, centerZ),
                size);
        }

        /// <summary>
        /// Battant libre d'un mur mobile. L'angle zéro est sa pose initiale déclarée
        /// dans la topologie : la donnée signée reste la seule origine du référentiel,
        /// jamais un transform de scène ni un nom d'objet.
        /// </summary>
        public static TopologyBladeSpec Blade(TopologyRuntimeMap map, int wallId)
        {
            if (map == null)
                throw new ArgumentNullException(nameof(map));
            var wall = map.GetWall(wallId);
            if (!wall.PivotId.HasValue)
                throw new ArgumentException($"Le mur {wallId} est statique.", nameof(wallId));

            var pivot = map.GetPivot(wall.PivotId.Value);
            var origin = wall.GetState(wall.InitialStateId);
            var pitch = map.Dimensions.CellPitchMm;
            return new TopologyBladeSpec(
                wallId,
                (2L * pivot.NodeX - map.Dimensions.WidthCells) * pitch,
                (2L * pivot.NodeY - map.Dimensions.HeightCells) * pitch,
                DirectionAtPivot(origin.Edge, pivot),
                pitch,
                map.Dimensions.WallThicknessMm);
        }

        /// <summary>
        /// Angle canonique d'une pose déclarée, relatif à la pose initiale. Il sert
        /// à poser l'angle de départ et à décrire une pose dans un diagnostic.
        /// </summary>
        public static int StateAngleMilliDegrees(TopologyRuntimeMap map, int wallId, int stateId)
        {
            if (map == null)
                throw new ArgumentNullException(nameof(map));
            var wall = map.GetWall(wallId);
            var origin = wall.GetState(wall.InitialStateId);
            var state = wall.GetState(stateId);
            return FixedTrigonometry.Normalize(
                (long)(state.QuarterTurns - origin.QuarterTurns) *
                FixedTrigonometry.QuarterTurnMilliDegrees);
        }

        public static TopologySweepSpec QuarterTurnSweep(
            TopologyRuntimeMap map,
            int wallId,
            int fromStateId,
            int toStateId)
        {
            var wall = map.GetWall(wallId);
            if (!wall.PivotId.HasValue)
                throw new ArgumentException($"Le mur {wallId} est statique.", nameof(wallId));
            var from = wall.GetState(fromStateId);
            var to = wall.GetState(toStateId);
            var delta = (to.QuarterTurns - from.QuarterTurns + 4) % 4;
            if (delta != 1 && delta != 3)
                throw new ArgumentException("Le sweep minimal exige deux poses adjacentes a 90 degres.", nameof(toStateId));

            var pivot = map.GetPivot(wall.PivotId.Value);
            var fromDirection = DirectionAtPivot(from.Edge, pivot);
            var pitch = map.Dimensions.CellPitchMm;
            return new TopologySweepSpec(
                wallId,
                (2L * pivot.NodeX - map.Dimensions.WidthCells) * pitch,
                (2L * pivot.NodeY - map.Dimensions.HeightCells) * pitch,
                fromDirection,
                delta == 1 ? 1 : -1,
                pitch,
                map.Dimensions.WallThicknessMm);
        }

        private static int DirectionAtPivot(TopologyEdgeKey edge, RuntimePivotDefinition pivot)
        {
            if (edge.Axis == TopologyAxis.Vertical && edge.X == pivot.NodeX)
            {
                if (edge.Y == pivot.NodeY)
                    return 0;
                if (edge.Y + 1 == pivot.NodeY)
                    return 2;
            }
            else if (edge.Axis == TopologyAxis.Horizontal && edge.Y == pivot.NodeY)
            {
                if (edge.X == pivot.NodeX)
                    return 1;
                if (edge.X + 1 == pivot.NodeX)
                    return 3;
            }
            throw new ArgumentException($"L'arete {edge} ne touche pas le pivot {pivot.PivotId}.", nameof(edge));
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
