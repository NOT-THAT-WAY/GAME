using System;

namespace NotThatWay.Game.Simulation
{
    /// <summary>
    /// Réglages du couple continu d'un battant. Tout est exprimé en ticks et en
    /// milli-degrés : la simulation ignore la fréquence d'affichage, le deltaTime
    /// et PhysX.
    /// </summary>
    public readonly struct WallSimulationSettings : IEquatable<WallSimulationSettings>
    {
        /// <summary>Un levier vaut 1000 pour mille au bout du battant.</summary>
        public const int PermilleScale = 1000;

        /// <summary>
        /// Pas de quantification du couple net. Sans lui, le moindre pas de côté du
        /// pousseur change la vitesse d'un milli-degré, donc ouvre un segment, donc
        /// diffuse un snapshot : le battant se synchroniserait à chaque tick, ce que
        /// le contrat réseau interdit. Quinze paliers entre le gond et le bout
        /// restent imperceptibles à l'œil et stables sur le réseau.
        /// </summary>
        public const int LeverageQuantumPermille = 50;

        public WallSimulationSettings(
            int maximumAngularSpeedMilliDegreesPerTick,
            int minimumLeveragePermille,
            uint maximumExtrapolationTicks)
        {
            if (maximumAngularSpeedMilliDegreesPerTick <= 0 ||
                maximumAngularSpeedMilliDegreesPerTick > FixedTrigonometry.QuarterTurnMilliDegrees)
            {
                throw new ArgumentOutOfRangeException(nameof(maximumAngularSpeedMilliDegreesPerTick));
            }
            if (minimumLeveragePermille < 0 || minimumLeveragePermille > PermilleScale)
                throw new ArgumentOutOfRangeException(nameof(minimumLeveragePermille));
            TickMath.ValidateDuration(maximumExtrapolationTicks);

            MaximumAngularSpeedMilliDegreesPerTick = maximumAngularSpeedMilliDegreesPerTick;
            MinimumLeveragePermille = minimumLeveragePermille;
            MaximumExtrapolationTicks = maximumExtrapolationTicks;
        }

        /// <summary>Vitesse atteinte par une poussée seule au bout du battant.</summary>
        public int MaximumAngularSpeedMilliDegreesPerTick { get; }

        /// <summary>Part de puissance conservée au contact du gond.</summary>
        public int MinimumLeveragePermille { get; }

        /// <summary>
        /// Borne l'avance libre d'un client entre deux snapshots. Le battement
        /// serveur étant plus court, cette borne ne sert qu'à empêcher un segment
        /// perdu de faire tourner le mur indéfiniment chez un observateur.
        /// </summary>
        public uint MaximumExtrapolationTicks { get; }

        public void Validate()
        {
            if (MaximumAngularSpeedMilliDegreesPerTick <= 0 ||
                MaximumAngularSpeedMilliDegreesPerTick > FixedTrigonometry.QuarterTurnMilliDegrees)
            {
                throw new ArgumentOutOfRangeException(nameof(MaximumAngularSpeedMilliDegreesPerTick));
            }
            if (MinimumLeveragePermille < 0 || MinimumLeveragePermille > PermilleScale)
                throw new ArgumentOutOfRangeException(nameof(MinimumLeveragePermille));
            TickMath.ValidateDuration(MaximumExtrapolationTicks);
        }

        /// <summary>
        /// Vitesse produite par un couple net, borné à ±1000 pour mille puis
        /// quantifié. La division entière tronque vers zéro : même verdict sur
        /// toute plateforme.
        /// </summary>
        public int VelocityFromNetLeverage(int netLeveragePermille)
        {
            var clamped = netLeveragePermille < -PermilleScale
                ? -PermilleScale
                : netLeveragePermille > PermilleScale
                    ? PermilleScale
                    : netLeveragePermille;
            var quantized = QuantizeLeverage(clamped);
            return (int)((long)quantized * MaximumAngularSpeedMilliDegreesPerTick / PermilleScale);
        }

        /// <summary>
        /// Arrondi entier au palier le plus proche, symétrique autour de zéro.
        /// </summary>
        public static int QuantizeLeverage(int netLeveragePermille)
        {
            var sign = netLeveragePermille < 0 ? -1 : 1;
            var magnitude = netLeveragePermille < 0
                ? -(long)netLeveragePermille
                : netLeveragePermille;
            var steps = (magnitude + LeverageQuantumPermille / 2) / LeverageQuantumPermille;
            return (int)(sign * steps * LeverageQuantumPermille);
        }

        public bool Equals(WallSimulationSettings other) =>
            MaximumAngularSpeedMilliDegreesPerTick == other.MaximumAngularSpeedMilliDegreesPerTick &&
            MinimumLeveragePermille == other.MinimumLeveragePermille &&
            MaximumExtrapolationTicks == other.MaximumExtrapolationTicks;

        public override bool Equals(object value) => value is WallSimulationSettings other && Equals(other);

        public override int GetHashCode() => HashCode.Combine(
            MaximumAngularSpeedMilliDegreesPerTick,
            MinimumLeveragePermille,
            MaximumExtrapolationTicks);
    }

    /// <summary>
    /// Intention de couple d'une source pour un tick. Le sens vaut ±1 et le levier
    /// dit à quelle distance du gond la poussée s'applique ; l'addition des deux
    /// produit la contre-poussée sans règle supplémentaire.
    /// </summary>
    public readonly struct WallTorqueIntent
    {
        public WallTorqueIntent(int wallId, int sourceId, int direction, int leveragePermille)
        {
            if (wallId <= 0)
                throw new ArgumentOutOfRangeException(nameof(wallId));
            if (sourceId < 0)
                throw new ArgumentOutOfRangeException(nameof(sourceId));
            if (direction != -1 && direction != 1)
                throw new ArgumentOutOfRangeException(nameof(direction));
            if (leveragePermille < 0 || leveragePermille > WallSimulationSettings.PermilleScale)
                throw new ArgumentOutOfRangeException(nameof(leveragePermille));

            WallId = wallId;
            SourceId = sourceId;
            Direction = direction;
            LeveragePermille = leveragePermille;
        }

        public int WallId { get; }
        public int SourceId { get; }
        public int Direction { get; }
        public int LeveragePermille { get; }
        public int SignedLeveragePermille => Direction * LeveragePermille;
    }

    /// <summary>
    /// État partagé d'un battant libre. Il ne transporte jamais un transform : un
    /// segment de mouvement — angle d'ancrage, tick d'ancrage, vitesse angulaire,
    /// révision — suffit à rejouer la pose de n'importe quel tick.
    /// </summary>
    public readonly struct WallState : IEquatable<WallState>
    {
        public WallState(int wallId, int angleMilliDegrees, uint anchorTick, uint revision = 0u)
            : this(wallId, angleMilliDegrees, 0, anchorTick, revision)
        {
        }

        public WallState(
            int wallId,
            int angleMilliDegrees,
            int angularVelocityMilliDegreesPerTick,
            uint anchorTick,
            uint revision)
        {
            if (wallId <= 0)
                throw new ArgumentOutOfRangeException(nameof(wallId));
            if (angleMilliDegrees < 0 || angleMilliDegrees >= FixedTrigonometry.FullTurnMilliDegrees)
                throw new ArgumentOutOfRangeException(nameof(angleMilliDegrees));
            if (Math.Abs(angularVelocityMilliDegreesPerTick) > FixedTrigonometry.QuarterTurnMilliDegrees)
                throw new ArgumentOutOfRangeException(nameof(angularVelocityMilliDegreesPerTick));

            WallId = wallId;
            AngleMilliDegrees = angleMilliDegrees;
            AngularVelocityMilliDegreesPerTick = angularVelocityMilliDegreesPerTick;
            AnchorTick = anchorTick;
            Revision = revision;
        }

        public int WallId { get; }

        /// <summary>Angle du battant au tick d'ancrage, dans [0, 360000).</summary>
        public int AngleMilliDegrees { get; }

        public int AngularVelocityMilliDegreesPerTick { get; }
        public uint AnchorTick { get; }
        public uint Revision { get; }
        public bool IsRotating => AngularVelocityMilliDegreesPerTick != 0;

        /// <summary>
        /// Pose logique d'un tick. En amont de l'ancrage la pose reste l'ancrage :
        /// un replay ne doit jamais inventer un passé que l'autorité n'a pas envoyé.
        /// </summary>
        public WallPoseSample SamplePose(uint tick, uint maximumExtrapolationTicks)
        {
            TickMath.ValidateDuration(maximumExtrapolationTicks);
            var elapsed = TickMath.Elapsed(AnchorTick, tick);
            if (elapsed > maximumExtrapolationTicks)
                elapsed = maximumExtrapolationTicks;
            var angle = FixedTrigonometry.Normalize(
                AngleMilliDegrees + (long)AngularVelocityMilliDegreesPerTick * elapsed);
            return new WallPoseSample(
                angle,
                AngularVelocityMilliDegreesPerTick,
                elapsed,
                IsRotating);
        }

        /// <summary>
        /// Deux états appartiennent au même segment quand leur sens et leur vitesse
        /// coïncident : entre deux snapshots d'un même segment, un client extrapole
        /// sans qu'aucun conflit de révision ne soit légitime.
        /// </summary>
        public bool SharesSegment(WallState other) =>
            WallId == other.WallId &&
            Revision == other.Revision &&
            AngularVelocityMilliDegreesPerTick == other.AngularVelocityMilliDegreesPerTick;

        public bool Equals(WallState other) =>
            WallId == other.WallId &&
            AngleMilliDegrees == other.AngleMilliDegrees &&
            AngularVelocityMilliDegreesPerTick == other.AngularVelocityMilliDegreesPerTick &&
            AnchorTick == other.AnchorTick &&
            Revision == other.Revision;

        public override bool Equals(object value) => value is WallState other && Equals(other);

        public override int GetHashCode() => HashCode.Combine(
            WallId, AngleMilliDegrees, AngularVelocityMilliDegreesPerTick, AnchorTick, Revision);
    }
}
