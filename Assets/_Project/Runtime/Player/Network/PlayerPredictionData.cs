using System;
using FishNet.Object.Prediction;
using NotThatWay.Game.PlayerSimulation;

namespace NotThatWay.Game.PlayerNetwork
{
    /// <summary>
    /// DTO mutable réservé au codegen FishNet. Le tick privé est fourni par FishNet,
    /// jamais par un champ gameplay contrôlé par le client.
    /// </summary>
    public struct PlayerReplicateData : IReplicateData
    {
        public sbyte MoveX;
        public sbyte MoveY;
        public short LookYaw;
        public short LookPitch;
        public ushort Buttons;

        private uint _tick;

        public PlayerReplicateData(PlayerCommand command)
        {
            MoveX = command.MoveX;
            MoveY = command.MoveY;
            LookYaw = command.LookYaw;
            LookPitch = command.LookPitch;
            Buttons = (ushort)command.Buttons;
            _tick = 0u;
        }

        public uint GetTick() => _tick;
        public void SetTick(uint value) => _tick = value;
        public void Dispose() { }

        public PlayerCommand ToCommand(uint simulationTick) => new(
            simulationTick,
            MoveX,
            MoveY,
            LookYaw,
            LookPitch,
            (PlayerCommandButtons)Buttons);

        /// <summary>
        /// Répétition prudente d'une intention future : direction et boutons tenus
        /// persistent, mais ni fronts ni delta de regard ne sont rejoués.
        /// </summary>
        public PlayerReplicateData WithoutOneShotInputs()
        {
            var result = this;
            result.LookYaw = 0;
            result.LookPitch = 0;
            result.Buttons &= (ushort)PlayerInputSample.HeldMask;
            return result;
        }
    }

    /// <summary>
    /// Snapshot complet de PLY-01, aplati en primitives sérialisables par FishNet/IL2CPP.
    /// </summary>
    public struct PlayerReconcileData : IReconcileData
    {
        public float PositionX;
        public float PositionY;
        public float PositionZ;
        public int YawCentidegrees;
        public int PitchCentidegrees;
        public float HorizontalVelocityX;
        public float HorizontalVelocityZ;
        public float VerticalVelocity;
        public float KnockbackVelocityX;
        public float KnockbackVelocityZ;
        public bool IsGrounded;
        public uint CoyoteTicksRemaining;
        public uint JumpBufferTicksRemaining;
        public bool IsDiving;
        public uint DiveRecoveryTicksRemaining;
        public uint DiveCooldownTicksRemaining;
        public bool IsCrawling;
        public uint SimulationTick;

        private uint _tick;

        public PlayerReconcileData(PlayerState state)
        {
            PositionX = ToFiniteFloat(state.Position.X, nameof(state.Position));
            PositionY = ToFiniteFloat(state.Position.Y, nameof(state.Position));
            PositionZ = ToFiniteFloat(state.Position.Z, nameof(state.Position));
            YawCentidegrees = state.YawCentidegrees;
            PitchCentidegrees = state.PitchCentidegrees;
            HorizontalVelocityX = ToFiniteFloat(
                state.HorizontalVelocity.X,
                nameof(state.HorizontalVelocity));
            HorizontalVelocityZ = ToFiniteFloat(
                state.HorizontalVelocity.Z,
                nameof(state.HorizontalVelocity));
            VerticalVelocity = ToFiniteFloat(state.VerticalVelocity, nameof(state.VerticalVelocity));
            KnockbackVelocityX = ToFiniteFloat(
                state.KnockbackVelocity.X,
                nameof(state.KnockbackVelocity));
            KnockbackVelocityZ = ToFiniteFloat(
                state.KnockbackVelocity.Z,
                nameof(state.KnockbackVelocity));
            IsGrounded = state.IsGrounded;
            CoyoteTicksRemaining = state.CoyoteTicksRemaining;
            JumpBufferTicksRemaining = state.JumpBufferTicksRemaining;
            IsDiving = state.IsDiving;
            DiveRecoveryTicksRemaining = state.DiveRecoveryTicksRemaining;
            DiveCooldownTicksRemaining = state.DiveCooldownTicksRemaining;
            IsCrawling = state.IsCrawling;
            SimulationTick = state.Tick;
            _tick = 0u;
        }

        public uint GetTick() => _tick;
        public void SetTick(uint value) => _tick = value;
        public void Dispose() { }

        public PlayerState ToState() => new(
            SimulationTick,
            new PlayerVector3(PositionX, PositionY, PositionZ),
            YawCentidegrees,
            PitchCentidegrees,
            new PlayerVector3(HorizontalVelocityX, 0d, HorizontalVelocityZ),
            VerticalVelocity,
            new PlayerVector3(KnockbackVelocityX, 0d, KnockbackVelocityZ),
            IsGrounded,
            CoyoteTicksRemaining,
            JumpBufferTicksRemaining,
            IsDiving,
            DiveRecoveryTicksRemaining,
            DiveCooldownTicksRemaining,
            IsCrawling);

        private static float ToFiniteFloat(double value, string parameterName)
        {
            if (double.IsNaN(value) || double.IsInfinity(value) ||
                value < -float.MaxValue || value > float.MaxValue)
            {
                throw new ArgumentOutOfRangeException(parameterName);
            }

            return (float)value;
        }
    }
}
