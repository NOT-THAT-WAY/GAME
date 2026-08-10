using System;

namespace NotThatWay.Game.Simulation
{
    /// <summary>
    /// Comparaisons de compteurs uint modulo 2^32. Deux valeurs ne doivent jamais
    /// être comparées à exactement un demi-espace (2^31 ticks), cas ambigu rejeté.
    /// </summary>
    public static class TickMath
    {
        public const ushort CompleteProgressQ16 = ushort.MaxValue;
        public const uint MaximumDurationTicks = int.MaxValue;

        public static uint Next(uint value) => unchecked(value + 1u);

        public static int Compare(uint left, uint right)
        {
            if (left == right)
                return 0;
            var delta = unchecked((int)(left - right));
            if (delta == int.MinValue)
                throw new ArgumentException("Écart de ticks ambigu à 2^31.");
            return delta > 0 ? 1 : -1;
        }

        public static bool IsNewer(uint candidate, uint reference) => Compare(candidate, reference) > 0;
        public static bool IsOlder(uint candidate, uint reference) => Compare(candidate, reference) < 0;
        public static bool IsNext(uint candidate, uint previous) => candidate == Next(previous);

        public static uint Elapsed(uint startTick, uint currentTick)
        {
            if (IsOlder(currentTick, startTick))
                return 0u;
            return unchecked(currentTick - startTick);
        }

        public static bool HasElapsed(uint startTick, uint durationTicks, uint currentTick)
        {
            ValidateDuration(durationTicks);
            return !IsOlder(currentTick, startTick) &&
                   unchecked(currentTick - startTick) >= durationTicks;
        }

        public static ushort ProgressQ16(uint startTick, uint durationTicks, uint currentTick)
        {
            ValidateDuration(durationTicks);
            if (IsOlder(currentTick, startTick))
                return 0;
            var elapsed = unchecked(currentTick - startTick);
            if (elapsed >= durationTicks)
                return CompleteProgressQ16;
            return (ushort)((ulong)elapsed * CompleteProgressQ16 / durationTicks);
        }

        public static void ValidateDuration(uint durationTicks)
        {
            if (durationTicks == 0u || durationTicks > MaximumDurationTicks)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(durationTicks),
                    durationTicks,
                    $"Une durée doit être comprise entre 1 et {MaximumDurationTicks} ticks.");
            }
        }
    }
}
