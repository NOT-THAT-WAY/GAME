using System;

namespace NotThatWay.Game.Sandbox
{
    public enum SandboxRoundPhase : byte
    {
        Waiting = 0,
        Countdown = 1,
        Playing = 2,
        Result = 3
    }

    [Flags]
    public enum SandboxRoundEvents : byte
    {
        None = 0,
        CountdownStarted = 1 << 0,
        RoundStarted = 1 << 1,
        RoundCompleted = 1 << 2,
        ResetRequested = 1 << 3
    }

    public readonly struct SandboxRoundConfig
    {
        public SandboxRoundConfig(
            int minimumPlayers,
            uint countdownTicks,
            uint playingTicks,
            uint resultTicks)
        {
            if (minimumPlayers <= 0)
                throw new ArgumentOutOfRangeException(nameof(minimumPlayers));
            if (countdownTicks == 0u)
                throw new ArgumentOutOfRangeException(nameof(countdownTicks));
            if (playingTicks == 0u)
                throw new ArgumentOutOfRangeException(nameof(playingTicks));
            if (resultTicks == 0u)
                throw new ArgumentOutOfRangeException(nameof(resultTicks));
            MinimumPlayers = minimumPlayers;
            CountdownTicks = countdownTicks;
            PlayingTicks = playingTicks;
            ResultTicks = resultTicks;
        }

        public int MinimumPlayers { get; }
        public uint CountdownTicks { get; }
        public uint PlayingTicks { get; }
        public uint ResultTicks { get; }
        public static SandboxRoundConfig Baseline60Hz => new(1, 180u, 5400u, 180u);
    }

    public readonly struct SandboxRoundState : IEquatable<SandboxRoundState>
    {
        public SandboxRoundState(
            uint tick,
            SandboxRoundPhase phase,
            uint phaseTicksRemaining,
            uint roundNumber,
            int winnerObjectId)
        {
            Tick = tick;
            Phase = phase;
            PhaseTicksRemaining = phaseTicksRemaining;
            RoundNumber = roundNumber;
            WinnerObjectId = winnerObjectId;
        }

        public uint Tick { get; }
        public SandboxRoundPhase Phase { get; }
        public uint PhaseTicksRemaining { get; }
        public uint RoundNumber { get; }
        public int WinnerObjectId { get; }
        public bool Equals(SandboxRoundState other) =>
            Tick == other.Tick &&
            Phase == other.Phase &&
            PhaseTicksRemaining == other.PhaseTicksRemaining &&
            RoundNumber == other.RoundNumber &&
            WinnerObjectId == other.WinnerObjectId;
        public override bool Equals(object value) =>
            value is SandboxRoundState other && Equals(other);
        public override int GetHashCode() =>
            HashCode.Combine(Tick, Phase, PhaseTicksRemaining, RoundNumber, WinnerObjectId);
    }

    public sealed class SandboxRoundModel
    {
        private readonly SandboxRoundConfig _config;
        private SandboxRoundState _state;

        public SandboxRoundModel(SandboxRoundConfig config)
        {
            _config = config;
            _state = new SandboxRoundState(0u, SandboxRoundPhase.Waiting, 0u, 1u, -1);
        }

        public SandboxRoundState State => _state;

        public SandboxRoundEvents AdvanceTick(int playerCount)
        {
            if (playerCount < 0)
                throw new ArgumentOutOfRangeException(nameof(playerCount));
            var tick = _state.Tick + 1u;
            var phase = _state.Phase;
            var remaining = _state.PhaseTicksRemaining;
            var round = _state.RoundNumber;
            var winner = _state.WinnerObjectId;
            var events = SandboxRoundEvents.None;

            switch (phase)
            {
                case SandboxRoundPhase.Waiting:
                    if (playerCount >= _config.MinimumPlayers)
                    {
                        phase = SandboxRoundPhase.Countdown;
                        remaining = _config.CountdownTicks;
                        winner = -1;
                        events |= SandboxRoundEvents.CountdownStarted;
                    }
                    break;
                case SandboxRoundPhase.Countdown:
                    if (playerCount < _config.MinimumPlayers)
                    {
                        phase = SandboxRoundPhase.Waiting;
                        remaining = 0u;
                    }
                    else if (CountDown(ref remaining))
                    {
                        phase = SandboxRoundPhase.Playing;
                        remaining = _config.PlayingTicks;
                        events |= SandboxRoundEvents.RoundStarted | SandboxRoundEvents.ResetRequested;
                    }
                    break;
                case SandboxRoundPhase.Playing:
                    if (CountDown(ref remaining))
                    {
                        phase = SandboxRoundPhase.Result;
                        remaining = _config.ResultTicks;
                        winner = -1;
                        events |= SandboxRoundEvents.RoundCompleted;
                    }
                    break;
                case SandboxRoundPhase.Result:
                    if (CountDown(ref remaining))
                    {
                        round++;
                        phase = playerCount >= _config.MinimumPlayers
                            ? SandboxRoundPhase.Countdown
                            : SandboxRoundPhase.Waiting;
                        remaining = phase == SandboxRoundPhase.Countdown
                            ? _config.CountdownTicks
                            : 0u;
                        winner = -1;
                        events |= SandboxRoundEvents.ResetRequested;
                        if (phase == SandboxRoundPhase.Countdown)
                            events |= SandboxRoundEvents.CountdownStarted;
                    }
                    break;
                default:
                    throw new ArgumentOutOfRangeException();
            }

            _state = new SandboxRoundState(tick, phase, remaining, round, winner);
            return events;
        }

        public bool TryComplete(int winnerObjectId)
        {
            if (winnerObjectId < 0)
                throw new ArgumentOutOfRangeException(nameof(winnerObjectId));
            if (_state.Phase != SandboxRoundPhase.Playing)
                return false;
            _state = new SandboxRoundState(
                _state.Tick,
                SandboxRoundPhase.Result,
                _config.ResultTicks,
                _state.RoundNumber,
                winnerObjectId);
            return true;
        }

        private static bool CountDown(ref uint value)
        {
            if (value > 0u)
                value--;
            return value == 0u;
        }
    }
}
