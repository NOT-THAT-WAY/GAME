using System;

namespace NotThatWay.Game.Simulation
{
    /// <summary>
    /// Sinus et cosinus entiers, des milli-degrés vers Q16. Un mur qui tourne
    /// librement n'a plus de pose alignée sur la grille : sa direction entre dans
    /// des règles partagées — côté du pousseur, bras de levier, balayage — dont le
    /// verdict doit être identique sous Mono et sous Windows IL2CPP. Math.Sin ne
    /// garantit pas cette égalité au dernier bit ; un CORDIC entier, si.
    /// </summary>
    public static class FixedTrigonometry
    {
        public const int Scale = 1 << 16;
        public const int QuarterTurnMilliDegrees = 90_000;
        public const int HalfTurnMilliDegrees = 180_000;
        public const int FullTurnMilliDegrees = 360_000;

        private const int InternalShift = 30;
        private const int OutputShift = InternalShift - 16;

        /// <summary>
        /// arctan(2^-i) en micro-degrés arrondis. La table est exprimée mille fois
        /// plus fin que l'angle d'entrée : son arrondi n'entre donc pas dans le
        /// résultat, et le résidu angulaire final reste sous le micro-degré.
        /// </summary>
        private static readonly int[] ArcTangentMicroDegrees =
        {
            45_000_000, 26_565_051, 14_036_243, 7_125_016, 3_576_334, 1_789_911,
            895_174, 447_614, 223_811, 111_906, 55_953, 27_976, 13_988, 6_994,
            3_497, 1_749, 874, 437, 219, 109, 55, 27, 14, 7, 3, 2, 1
        };

        private const int MicroDegreesPerMilliDegree = 1000;

        /// <summary>Inverse du gain CORDIC de ces 27 itérations, en Q30.</summary>
        private const long InverseGainQ30 = 652_032_874L;

        /// <summary>Ramène un angle quelconque dans [0, 360000).</summary>
        public static int Normalize(long milliDegrees)
        {
            var wrapped = milliDegrees % FullTurnMilliDegrees;
            if (wrapped < 0L)
                wrapped += FullTurnMilliDegrees;
            return (int)wrapped;
        }

        /// <summary>
        /// Écart signé le plus court entre deux angles, dans (-180000, 180000].
        /// </summary>
        public static int SignedDelta(int fromMilliDegrees, int toMilliDegrees)
        {
            var delta = Normalize((long)toMilliDegrees - fromMilliDegrees);
            return delta > HalfTurnMilliDegrees ? delta - FullTurnMilliDegrees : delta;
        }

        public static void SinCos(int milliDegrees, out int sinQ16, out int cosQ16)
        {
            var angle = Normalize(milliDegrees);
            var quadrant = angle / QuarterTurnMilliDegrees;
            var residual = angle - quadrant * QuarterTurnMilliDegrees;

            int quarterSin;
            int quarterCos;
            if (residual == 0)
            {
                // Les quatre poses cardinales doivent rester exactes : elles sont
                // les seules à devoir coïncider au millimètre près avec les arêtes
                // de la topologie.
                quarterSin = 0;
                quarterCos = Scale;
            }
            else
            {
                Rotate(residual, out quarterSin, out quarterCos);
            }

            switch (quadrant)
            {
                case 0:
                    sinQ16 = quarterSin;
                    cosQ16 = quarterCos;
                    return;
                case 1:
                    sinQ16 = quarterCos;
                    cosQ16 = -quarterSin;
                    return;
                case 2:
                    sinQ16 = -quarterSin;
                    cosQ16 = -quarterCos;
                    return;
                case 3:
                    sinQ16 = -quarterCos;
                    cosQ16 = quarterSin;
                    return;
                default:
                    throw new InvalidOperationException($"Quadrant hors domaine: {quadrant}.");
            }
        }

        public static int Sin(int milliDegrees)
        {
            SinCos(milliDegrees, out var sinQ16, out _);
            return sinQ16;
        }

        public static int Cos(int milliDegrees)
        {
            SinCos(milliDegrees, out _, out var cosQ16);
            return cosQ16;
        }

        /// <summary>CORDIC en mode rotation sur un angle de [1, 90000) milli-degrés.</summary>
        private static void Rotate(int residualMilliDegrees, out int sinQ16, out int cosQ16)
        {
            var x = InverseGainQ30;
            var y = 0L;
            var z = residualMilliDegrees * MicroDegreesPerMilliDegree;

            for (var index = 0; index < ArcTangentMicroDegrees.Length; index++)
            {
                var direction = z >= 0 ? 1 : -1;
                var shiftedX = x >> index;
                var shiftedY = y >> index;
                if (direction > 0)
                {
                    x -= shiftedY;
                    y += shiftedX;
                }
                else
                {
                    x += shiftedY;
                    y -= shiftedX;
                }
                z -= direction * ArcTangentMicroDegrees[index];
            }

            sinQ16 = (int)RoundShift(y);
            cosQ16 = (int)RoundShift(x);
        }

        private static long RoundShift(long value)
        {
            var rounded = (value + (1L << (OutputShift - 1))) >> OutputShift;
            return rounded > Scale ? Scale : rounded < -Scale ? -Scale : rounded;
        }
    }
}
