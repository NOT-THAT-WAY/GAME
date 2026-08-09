using System;

namespace NotThatWay.Game.PlayerSimulation
{
    /// <summary>
    /// Vecteur métrique indépendant de Unity. Le modèle joueur reste ainsi testable
    /// sans scène ni moteur physique ; l'adaptateur convertit aux frontières.
    /// </summary>
    public readonly struct PlayerVector3 : IEquatable<PlayerVector3>
    {
        public PlayerVector3(double x, double y, double z)
        {
            EnsureFinite(x, nameof(x));
            EnsureFinite(y, nameof(y));
            EnsureFinite(z, nameof(z));
            X = x;
            Y = y;
            Z = z;
        }

        public double X { get; }
        public double Y { get; }
        public double Z { get; }
        public double HorizontalMagnitude => Math.Sqrt(X * X + Z * Z);

        public static PlayerVector3 Zero => default;

        public PlayerVector3 WithY(double y) => new(X, y, Z);

        public static PlayerVector3 operator +(PlayerVector3 left, PlayerVector3 right) =>
            new(left.X + right.X, left.Y + right.Y, left.Z + right.Z);

        public static PlayerVector3 operator -(PlayerVector3 left, PlayerVector3 right) =>
            new(left.X - right.X, left.Y - right.Y, left.Z - right.Z);

        public static PlayerVector3 operator *(PlayerVector3 value, double scalar)
        {
            EnsureFinite(scalar, nameof(scalar));
            return new PlayerVector3(value.X * scalar, value.Y * scalar, value.Z * scalar);
        }

        public bool Equals(PlayerVector3 other) =>
            X.Equals(other.X) && Y.Equals(other.Y) && Z.Equals(other.Z);

        public override bool Equals(object value) => value is PlayerVector3 other && Equals(other);
        public override int GetHashCode() => HashCode.Combine(X, Y, Z);

        private static void EnsureFinite(double value, string parameterName)
        {
            if (double.IsNaN(value) || double.IsInfinity(value))
                throw new ArgumentOutOfRangeException(parameterName);
        }
    }
}
