using System;
using NotThatWay.Game.PlayerSimulation;

namespace NotThatWay.Game.Sandbox
{
    /// <summary>
    /// Photographie, pour un tick donné, de l'état de jeu qui pèse sur la
    /// locomotion : vie, trophée, énergie encore payable pour le sprint et objet
    /// tenu en main. Ces quatre valeurs viennent de champs répliqués qui ne sont
    /// pas dans <c>PlayerReconcileData</c> : les relire au moment du rejeu
    /// donnerait au tick N l'état de « maintenant » au lieu de l'état de N. Le
    /// contexte est donc capturé au premier passage du tick, puis rejoué tel
    /// quel — voir <see cref="SandboxCommandContextHistory"/>.
    ///
    /// La structure est pure et sans dépendance Unity : filtre et modificateur
    /// se testent en EditMode sans scène ni réseau.
    /// </summary>
    public readonly struct SandboxCommandContext : IEquatable<SandboxCommandContext>
    {
        public SandboxCommandContext(
            bool alive,
            bool hasTrophy,
            bool canSprint,
            bool hasSlingshotInHand,
            int movementPermille,
            int aimMovementPermille)
        {
            if (movementPermille < 0 || movementPermille > SandboxGameplayConfig.PermilleScale)
                throw new ArgumentOutOfRangeException(nameof(movementPermille));
            if (aimMovementPermille < 1 || aimMovementPermille > SandboxGameplayConfig.PermilleScale)
                throw new ArgumentOutOfRangeException(nameof(aimMovementPermille));

            Alive = alive;
            HasTrophy = hasTrophy;
            CanSprint = canSprint;
            HasSlingshotInHand = hasSlingshotInHand;
            MovementPermille = movementPermille;
            AimMovementPermille = aimMovementPermille;
        }

        public bool Alive { get; }
        public bool HasTrophy { get; }
        public bool CanSprint { get; }
        public bool HasSlingshotInHand { get; }

        /// <summary>Base de vitesse du tick, KO et trophée déjà pris en compte.</summary>
        public int MovementPermille { get; }

        /// <summary>Ralentissement appliqué tant que le lance-pierre est bandé.</summary>
        public int AimMovementPermille { get; }

        /// <summary>Contexte d'un joueur sans couche sandbox : rien n'est bridé.</summary>
        public static SandboxCommandContext Unrestricted => new(
            true,
            false,
            true,
            false,
            SandboxGameplayConfig.PermilleScale,
            SandboxGameplayConfig.PermilleScale);

        /// <summary>
        /// Un joueur KO garde son regard mais aucune intention physique ; le
        /// trophée coupe la poussée, et le sprint disparaît dès que son prochain
        /// prélèvement ne peut plus être payé.
        /// </summary>
        public PlayerCommand Filter(PlayerCommand command)
        {
            if (!Alive)
            {
                return new PlayerCommand(
                    command.Tick,
                    0,
                    0,
                    command.LookYaw,
                    command.LookPitch,
                    PlayerCommandButtons.None);
            }

            var buttons = command.Buttons;
            if (!CanSprint)
                buttons &= ~PlayerCommandButtons.SprintHeld;
            if (HasTrophy)
                buttons &= ~PlayerCommandButtons.InteractHeld;
            return new PlayerCommand(
                command.Tick,
                command.MoveX,
                command.MoveY,
                command.LookYaw,
                command.LookPitch,
                buttons);
        }

        /// <summary>
        /// Vitesse du tick : la base, puis le ralentissement de visée si le
        /// joueur bande le lance-pierre. Jamais zéro tant qu'il est vivant —
        /// viser ralentit, ne cloue pas au sol.
        /// </summary>
        public int MovementPermilleFor(PlayerCommand command)
        {
            var permille = MovementPermille;
            if (permille > 0 &&
                HasSlingshotInHand &&
                command.Has(PlayerCommandButtons.PunchHeld))
            {
                permille = (int)((long)permille * AimMovementPermille /
                                 SandboxGameplayConfig.PermilleScale);
                if (permille < 1)
                    permille = 1;
            }
            return permille;
        }

        public bool Equals(SandboxCommandContext other) =>
            Alive == other.Alive &&
            HasTrophy == other.HasTrophy &&
            CanSprint == other.CanSprint &&
            HasSlingshotInHand == other.HasSlingshotInHand &&
            MovementPermille == other.MovementPermille &&
            AimMovementPermille == other.AimMovementPermille;

        public override bool Equals(object value) =>
            value is SandboxCommandContext other && Equals(other);

        public override int GetHashCode() => HashCode.Combine(
            Alive, HasTrophy, CanSprint, HasSlingshotInHand, MovementPermille, AimMovementPermille);
    }

    /// <summary>
    /// Anneau des contextes déjà joués, indexé par tick de simulation. Le
    /// propriétaire enregistre au premier passage d'un tick et relit pendant la
    /// réconciliation ; l'hôte, qui ne rejoue jamais, écrit sans jamais relire.
    ///
    /// La capacité couvre la fenêtre de prédiction utile (2 s à 60 Hz). Au-delà,
    /// <see cref="TryGet"/> répond faux plutôt que de rendre le contexte d'un
    /// tick voisin : mieux vaut retomber sur l'état courant que mentir sur un
    /// tick que l'anneau a déjà oublié.
    /// </summary>
    public sealed class SandboxCommandContextHistory
    {
        public const int Capacity = 128;

        private readonly SandboxCommandContext[] _contexts = new SandboxCommandContext[Capacity];
        private readonly uint[] _ticks = new uint[Capacity];
        private readonly bool[] _written = new bool[Capacity];

        public void Record(uint tick, in SandboxCommandContext context)
        {
            var slot = (int)(tick % Capacity);
            _contexts[slot] = context;
            _ticks[slot] = tick;
            _written[slot] = true;
        }

        public bool TryGet(uint tick, out SandboxCommandContext context)
        {
            var slot = (int)(tick % Capacity);
            if (_written[slot] && _ticks[slot] == tick)
            {
                context = _contexts[slot];
                return true;
            }
            context = default;
            return false;
        }

        public void Clear() => Array.Clear(_written, 0, _written.Length);
    }
}
