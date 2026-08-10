using System;
using System.Collections.Generic;
using NotThatWay.Game.PlayerSimulation;
using NotThatWay.Game.Simulation;

namespace NotThatWay.Game.PlayerNetwork
{
    public enum M1AutomatedPlayerProfile : byte
    {
        None = 0,
        ClearSweep = 1,
        InteractAfter120 = 2,
        InteractAfter180 = 3
    }

    /// <summary>
    /// Source déterministe réservée aux builds Development du banc M1. Elle injecte
    /// les mêmes commandes par tick que le chemin clavier, sans contourner Replicate.
    /// </summary>
    public readonly struct M1AutomatedCommandSource
    {
        private const string ArgumentName = "--m1-auto-player";

        public M1AutomatedCommandSource(
            M1AutomatedPlayerProfile profile,
            bool wasSpecified = true)
        {
            Profile = profile;
            WasSpecified = wasSpecified;
        }

        public M1AutomatedPlayerProfile Profile { get; }
        public bool Enabled => Profile != M1AutomatedPlayerProfile.None;
        public bool WasSpecified { get; }

        public string Name
        {
            get
            {
                switch (Profile)
                {
                    case M1AutomatedPlayerProfile.ClearSweep:
                        return "clear-sweep";
                    case M1AutomatedPlayerProfile.InteractAfter120:
                        return "interact-120";
                    case M1AutomatedPlayerProfile.InteractAfter180:
                        return "interact-180";
                    default:
                        return "none";
                }
            }
        }

        public PlayerCommand CreateCommand(uint simulationTick)
        {
            switch (Profile)
            {
                case M1AutomatedPlayerProfile.ClearSweep:
                    return new PlayerCommand(
                        simulationTick,
                        0,
                        simulationTick <= 45u ? (sbyte)127 : (sbyte)0,
                        0,
                        0,
                        PlayerCommandButtons.None);
                // Appui maintenu jusqu'à la fin : le seuil d'effort d'une porte
                // lourde se compte en secondes, une fenêtre fixe le manquerait.
                case M1AutomatedPlayerProfile.InteractAfter120:
                    return InteractDuring(simulationTick, 120u, uint.MaxValue);
                case M1AutomatedPlayerProfile.InteractAfter180:
                    return InteractDuring(simulationTick, 180u, uint.MaxValue);
                default:
                    return new PlayerCommand(
                        simulationTick, 0, 0, 0, 0, PlayerCommandButtons.None);
            }
        }

        public static bool TryParseArguments(
            IReadOnlyList<string> arguments,
            out M1AutomatedCommandSource source,
            out string error)
        {
            source = default;
            error = string.Empty;
            if (arguments == null)
            {
                error = "arguments_null";
                return false;
            }

            string value = null;
            for (var index = 0; index < arguments.Count; index++)
            {
                var argument = arguments[index] ?? string.Empty;
                var prefix = ArgumentName + "=";
                if (argument.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                {
                    if (value != null)
                    {
                        error = "profile_duplicate";
                        return false;
                    }
                    value = argument.Substring(prefix.Length);
                    continue;
                }
                if (!string.Equals(argument, ArgumentName, StringComparison.OrdinalIgnoreCase))
                    continue;
                if (value != null || index + 1 >= arguments.Count)
                {
                    error = value != null ? "profile_duplicate" : "profile_value_missing";
                    return false;
                }
                value = arguments[++index];
            }

            if (value == null)
                return true;

            M1AutomatedPlayerProfile profile;
            switch (value.Trim().ToLowerInvariant())
            {
                case "none":
                    profile = M1AutomatedPlayerProfile.None;
                    break;
                case "clear-sweep":
                    profile = M1AutomatedPlayerProfile.ClearSweep;
                    break;
                case "interact-120":
                    profile = M1AutomatedPlayerProfile.InteractAfter120;
                    break;
                case "interact-180":
                    profile = M1AutomatedPlayerProfile.InteractAfter180;
                    break;
                default:
                    error = "profile_unknown";
                    return false;
            }

            source = new M1AutomatedCommandSource(profile);
            return true;
        }

        private static PlayerCommand InteractDuring(
            uint simulationTick,
            uint startTick,
            uint durationTicks)
        {
            var elapsed = unchecked(simulationTick - startTick);
            var held = !TickMath.IsOlder(simulationTick, startTick) && elapsed < durationTicks;
            var buttons = held
                ? PlayerCommandButtons.InteractHeld
                : PlayerCommandButtons.None;
            return new PlayerCommand(simulationTick, 0, 0, 0, 0, buttons);
        }
    }
}
