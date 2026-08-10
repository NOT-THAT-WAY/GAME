using System;

namespace NotThatWay.Game.PlayerSimulation
{
    public static class PlayerCommandEncoder
    {
        public const int AxisMagnitude = 127;
        public const int LookUnitsPerDegree = 100;

        public static PlayerCommand Encode(
            uint tick,
            double moveX,
            double moveY,
            double lookYawDegrees,
            double lookPitchDegrees,
            PlayerCommandButtons buttons)
        {
            EnsureFinite(moveX, nameof(moveX));
            EnsureFinite(moveY, nameof(moveY));
            EnsureFinite(lookYawDegrees, nameof(lookYawDegrees));
            EnsureFinite(lookPitchDegrees, nameof(lookPitchDegrees));

            var maximumComponent = Math.Max(Math.Abs(moveX), Math.Abs(moveY));
            if (maximumComponent > 0d)
            {
                var scaledX = moveX / maximumComponent;
                var scaledY = moveY / maximumComponent;
                var scaledMagnitude = Math.Sqrt(scaledX * scaledX + scaledY * scaledY);
                if (maximumComponent * scaledMagnitude > 1d)
                {
                    moveX = scaledX / scaledMagnitude;
                    moveY = scaledY / scaledMagnitude;
                }
            }

            return new PlayerCommand(
                tick,
                QuantizeAxis(moveX),
                QuantizeAxis(moveY),
                QuantizeLookDegrees(lookYawDegrees),
                QuantizeLookDegrees(lookPitchDegrees),
                buttons);
        }

        public static double DecodeAxis(sbyte value) => value / (double)AxisMagnitude;
        public static double DecodeLookDegrees(short value) => value / (double)LookUnitsPerDegree;

        private static sbyte QuantizeAxis(double value)
        {
            var scaled = Math.Round(value * AxisMagnitude, MidpointRounding.AwayFromZero);
            return (sbyte)Clamp(scaled, -AxisMagnitude, AxisMagnitude);
        }

        private static short QuantizeLookDegrees(double value)
        {
            var scaled = Math.Round(value * LookUnitsPerDegree, MidpointRounding.AwayFromZero);
            return (short)Clamp(scaled, short.MinValue, short.MaxValue);
        }

        private static double Clamp(double value, double minimum, double maximum) =>
            value < minimum ? minimum : value > maximum ? maximum : value;

        private static void EnsureFinite(double value, string parameterName)
        {
            if (double.IsNaN(value) || double.IsInfinity(value))
                throw new ArgumentOutOfRangeException(parameterName);
        }
    }
}
