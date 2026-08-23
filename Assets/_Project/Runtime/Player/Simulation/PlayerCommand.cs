using System;

namespace NotThatWay.Game.PlayerSimulation
{
    [Flags]
    public enum PlayerCommandButtons : ushort
    {
        None = 0,
        SprintHeld = 1 << 0,
        InteractHeld = 1 << 1,
        PunchHeld = 1 << 2,
        SlingshotHeld = 1 << 3,
        SlingshotPressed = 1 << 5,
        JumpPressed = 1 << 8,
        InteractPressed = 1 << 9,
        PunchPressed = 1 << 10,
        DropPressed = 1 << 11,
        SelectSlot1Pressed = 1 << 12,
        SelectSlot2Pressed = 1 << 13,
        SelectSlot3Pressed = 1 << 14,
        CycleSlotPressed = 1 << 15
    }

    /// <summary>
    /// Intention compacte consommée une fois par tick. Les axes utilisent
    /// [-127, 127] et le regard des centièmes de degré bornés sur un <see cref="short"/>.
    /// </summary>
    public readonly struct PlayerCommand : IEquatable<PlayerCommand>
    {
        public PlayerCommand(
            uint tick,
            sbyte moveX,
            sbyte moveY,
            short lookYaw,
            short lookPitch,
            PlayerCommandButtons buttons)
        {
            Tick = tick;
            MoveX = moveX;
            MoveY = moveY;
            LookYaw = lookYaw;
            LookPitch = lookPitch;
            Buttons = buttons;
        }

        public uint Tick { get; }
        public sbyte MoveX { get; }
        public sbyte MoveY { get; }
        public short LookYaw { get; }
        public short LookPitch { get; }
        public PlayerCommandButtons Buttons { get; }

        public bool Has(PlayerCommandButtons button) => (Buttons & button) != 0;

        public bool Equals(PlayerCommand other) =>
            Tick == other.Tick &&
            MoveX == other.MoveX &&
            MoveY == other.MoveY &&
            LookYaw == other.LookYaw &&
            LookPitch == other.LookPitch &&
            Buttons == other.Buttons;

        public override bool Equals(object value) => value is PlayerCommand other && Equals(other);
        public override int GetHashCode() => HashCode.Combine(
            Tick, MoveX, MoveY, LookYaw, LookPitch, Buttons);
    }

    /// <summary>
    /// Échantillon non quantifié d'une frame Unity. Les boutons continus et les
    /// fronts sont séparés afin qu'un appui complet entre deux ticks ne soit pas perdu.
    /// </summary>
    public readonly struct PlayerInputSample
    {
        public const PlayerCommandButtons HeldMask =
            PlayerCommandButtons.SprintHeld |
            PlayerCommandButtons.InteractHeld |
            PlayerCommandButtons.PunchHeld |
            PlayerCommandButtons.SlingshotHeld;

        public const PlayerCommandButtons PressedMask =
            PlayerCommandButtons.SlingshotPressed |
            PlayerCommandButtons.JumpPressed |
            PlayerCommandButtons.InteractPressed |
            PlayerCommandButtons.PunchPressed |
            PlayerCommandButtons.DropPressed |
            PlayerCommandButtons.SelectSlot1Pressed |
            PlayerCommandButtons.SelectSlot2Pressed |
            PlayerCommandButtons.SelectSlot3Pressed |
            PlayerCommandButtons.CycleSlotPressed;

        public PlayerInputSample(
            float moveX,
            float moveY,
            float lookYawDegrees,
            float lookPitchDegrees,
            PlayerCommandButtons heldButtons,
            PlayerCommandButtons pressedButtons)
        {
            EnsureFinite(moveX, nameof(moveX));
            EnsureFinite(moveY, nameof(moveY));
            EnsureFinite(lookYawDegrees, nameof(lookYawDegrees));
            EnsureFinite(lookPitchDegrees, nameof(lookPitchDegrees));
            if ((heldButtons & ~HeldMask) != 0)
                throw new ArgumentOutOfRangeException(nameof(heldButtons));
            if ((pressedButtons & ~PressedMask) != 0)
                throw new ArgumentOutOfRangeException(nameof(pressedButtons));

            MoveX = moveX;
            MoveY = moveY;
            LookYawDegrees = lookYawDegrees;
            LookPitchDegrees = lookPitchDegrees;
            HeldButtons = heldButtons;
            PressedButtons = pressedButtons;
        }

        public float MoveX { get; }
        public float MoveY { get; }
        public float LookYawDegrees { get; }
        public float LookPitchDegrees { get; }
        public PlayerCommandButtons HeldButtons { get; }
        public PlayerCommandButtons PressedButtons { get; }

        private static void EnsureFinite(float value, string parameterName)
        {
            if (float.IsNaN(value) || float.IsInfinity(value))
                throw new ArgumentOutOfRangeException(parameterName);
        }
    }
}
