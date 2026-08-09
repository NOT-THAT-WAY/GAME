using System;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>Indices stables partagés par le gameplay, les queries et les tests.</summary>
    public static class GameplayLayers
    {
        public const int World = 8;
        public const int Player = 9;
        public const int InteractionQuery = 10;
        public const int VisualOnly = 11;

        public const string WorldName = "GameplayWorld";
        public const string PlayerName = "Player";
        public const string InteractionQueryName = "InteractionQuery";
        public const string VisualOnlyName = "VisualOnly";

        public static void ValidateProjectConfiguration()
        {
            Validate(World, WorldName);
            Validate(Player, PlayerName);
            Validate(InteractionQuery, InteractionQueryName);
            Validate(VisualOnly, VisualOnlyName);

            for (var first = 0; first < 32; first++)
            {
                for (var second = first; second < 32; second++)
                {
                    var expectedCollision = ShouldCollide(first, second);
                    var actualCollision = !Physics.GetIgnoreLayerCollision(first, second);
                    if (actualCollision != expectedCollision)
                    {
                        throw new InvalidOperationException(
                            $"Matrice physique invalide pour les layers {first}/{second}: " +
                            $"collision={actualCollision}, attendu={expectedCollision}.");
                    }
                }
            }
        }

        public static bool ShouldCollide(int first, int second)
        {
            if (first is < 0 or > 31)
                throw new ArgumentOutOfRangeException(nameof(first));
            if (second is < 0 or > 31)
                throw new ArgumentOutOfRangeException(nameof(second));
            if (first == InteractionQuery || first == VisualOnly ||
                second == InteractionQuery || second == VisualOnly)
                return false;
            if (first == World || second == World)
                return first == World && second == Player || first == Player && second == World;
            if (first == Player || second == Player)
                return first == Player && second == Player;
            return true;
        }

        private static void Validate(int index, string expectedName)
        {
            var actualName = LayerMask.LayerToName(index);
            if (!string.Equals(actualName, expectedName, StringComparison.Ordinal))
            {
                throw new InvalidOperationException(
                    $"Layer {index} invalide: '{actualName}', attendu '{expectedName}'.");
            }
        }
    }
}
