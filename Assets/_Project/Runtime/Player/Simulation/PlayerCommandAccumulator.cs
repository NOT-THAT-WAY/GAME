namespace NotThatWay.Game.PlayerSimulation
{
    /// <summary>
    /// Pont frame → tick. Le déplacement et les boutons tenus gardent la dernière
    /// valeur ; les deltas de regard s'additionnent et les fronts restent mémorisés
    /// jusqu'à leur consommation unique.
    /// </summary>
    public sealed class PlayerCommandAccumulator
    {
        private double _moveX;
        private double _moveY;
        private double _lookYawDegrees;
        private double _lookPitchDegrees;
        private PlayerCommandButtons _heldButtons;
        private PlayerCommandButtons _pressedButtons;

        public void Accumulate(PlayerInputSample sample)
        {
            _moveX = sample.MoveX;
            _moveY = sample.MoveY;
            _lookYawDegrees += sample.LookYawDegrees;
            _lookPitchDegrees += sample.LookPitchDegrees;
            _heldButtons = sample.HeldButtons;
            _pressedButtons |= sample.PressedButtons;
        }

        public PlayerCommand Consume(uint tick)
        {
            var command = PlayerCommandEncoder.Encode(
                tick,
                _moveX,
                _moveY,
                _lookYawDegrees,
                _lookPitchDegrees,
                _heldButtons | _pressedButtons);

            _lookYawDegrees = 0d;
            _lookPitchDegrees = 0d;
            _pressedButtons = PlayerCommandButtons.None;
            return command;
        }

        public void Reset()
        {
            _moveX = 0d;
            _moveY = 0d;
            _lookYawDegrees = 0d;
            _lookPitchDegrees = 0d;
            _heldButtons = PlayerCommandButtons.None;
            _pressedButtons = PlayerCommandButtons.None;
        }
    }
}
