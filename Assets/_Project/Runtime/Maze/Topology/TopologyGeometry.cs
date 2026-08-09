using System;
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
