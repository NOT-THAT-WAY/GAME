using System;
using NotThatWay.Game.Topology;

namespace NotThatWay.Game.Simulation
{
    public enum M1WallInteractionRejection : byte
    {
        None = 0,
        WallMissing = 1,
        WallStatic = 2,
        OutOfReach = 3,

        /// <summary>Centre exactement dans le plan du battant : aucun côté déductible.</summary>
        CenterOnWallPlane = 4
    }

    public readonly struct M1WallInteractionDecision
    {
        private M1WallInteractionDecision(
            bool allowed,
            int direction,
            int contactPermille,
            int leveragePermille,
            M1WallInteractionRejection rejection)
        {
            Allowed = allowed;
            Direction = direction;
            ContactPermille = contactPermille;
            LeveragePermille = leveragePermille;
            Rejection = rejection;
        }

        public bool Allowed { get; }

        /// <summary>Sens de rotation imposé par la position du pousseur, ±1.</summary>
        public int Direction { get; }

        /// <summary>Abscisse du contact : 0 au gond, 1000 au bout du battant.</summary>
        public int ContactPermille { get; }

        /// <summary>Part de la vitesse maximale accordée par ce bras de levier.</summary>
        public int LeveragePermille { get; }

        public M1WallInteractionRejection Rejection { get; }

        public static M1WallInteractionDecision Accept(
            int direction,
            int contactPermille,
            int leveragePermille)
        {
            if (direction != -1 && direction != 1)
                throw new ArgumentOutOfRangeException(nameof(direction));
            if (contactPermille < 0 || contactPermille > WallSimulationSettings.PermilleScale)
                throw new ArgumentOutOfRangeException(nameof(contactPermille));
            if (leveragePermille < 0 || leveragePermille > WallSimulationSettings.PermilleScale)
                throw new ArgumentOutOfRangeException(nameof(leveragePermille));
            return new M1WallInteractionDecision(
                true,
                direction,
                contactPermille,
                leveragePermille,
                M1WallInteractionRejection.None);
        }

        public static M1WallInteractionDecision Reject(M1WallInteractionRejection rejection)
        {
            if (rejection == M1WallInteractionRejection.None)
                throw new ArgumentOutOfRangeException(nameof(rejection));
            return new M1WallInteractionDecision(false, 0, 0, 0, rejection);
        }
    }

    /// <summary>
    /// Règle de contact du banc M1. Le client ne choisit qu'entre maintenir et
    /// relâcher : l'hôte recalcule sur sa propre pose quantifiée si le pousseur
    /// touche le battant, de quel côté il se trouve — donc dans quel sens le mur
    /// s'éloigne de lui — et quel bras de levier sa position lui accorde.
    /// </summary>
    public static class M1WallInteractionRules
    {
        public static M1WallInteractionDecision Evaluate(
            TopologyRuntimeMap map,
            int wallId,
            int angleMilliDegrees,
            int playerCenterXMm,
            int playerCenterZMm,
            int playerRadiusMm,
            int reachFromCapsuleMm,
            int minimumLeveragePermille)
        {
            if (map == null)
                throw new ArgumentNullException(nameof(map));
            if (playerRadiusMm < 0)
                throw new ArgumentOutOfRangeException(nameof(playerRadiusMm));
            if (reachFromCapsuleMm < 0)
                throw new ArgumentOutOfRangeException(nameof(reachFromCapsuleMm));
            if (minimumLeveragePermille < 0 ||
                minimumLeveragePermille > WallSimulationSettings.PermilleScale)
            {
                throw new ArgumentOutOfRangeException(nameof(minimumLeveragePermille));
            }

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

            var contact = TopologyGeometry
                .Blade(map, wallId)
                .Probe(
                    angleMilliDegrees,
                    playerCenterXMm,
                    playerCenterZMm,
                    playerRadiusMm,
                    reachFromCapsuleMm);
            if (!contact.WithinReach)
                return M1WallInteractionDecision.Reject(M1WallInteractionRejection.OutOfReach);
            if (contact.LateralSign == 0)
                return M1WallInteractionDecision.Reject(M1WallInteractionRejection.CenterOnWallPlane);

            // Règle de la porte : le battant s'éloigne toujours de celui qui pousse.
            // Une rotation positive l'emmène vers le demi-plan de signe positif, donc
            // pousser depuis ce demi-plan impose la rotation négative, et inversement.
            // Se déplacer de l'autre côté du battant suffit à inverser le sens, sur
            // les 360 degrés, sans pose ni état de destination.
            return M1WallInteractionDecision.Accept(
                -contact.LateralSign,
                contact.ContactPermille,
                Leverage(contact.ContactPermille, minimumLeveragePermille));
        }

        /// <summary>
        /// Interpolation entière du bras de levier : la puissance minimale au gond,
        /// la pleine puissance au bout, au prorata de l'abscisse du contact.
        /// </summary>
        public static int Leverage(int contactPermille, int minimumLeveragePermille)
        {
            if (contactPermille < 0 || contactPermille > WallSimulationSettings.PermilleScale)
                throw new ArgumentOutOfRangeException(nameof(contactPermille));
            if (minimumLeveragePermille < 0 ||
                minimumLeveragePermille > WallSimulationSettings.PermilleScale)
            {
                throw new ArgumentOutOfRangeException(nameof(minimumLeveragePermille));
            }

            var span = WallSimulationSettings.PermilleScale - minimumLeveragePermille;
            return minimumLeveragePermille +
                   (int)((long)span * contactPermille / WallSimulationSettings.PermilleScale);
        }
    }
}
