using System;
using System.Collections.Generic;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Active le smoke test humain local. Ce mode ne change aucune règle : il
    /// simplifie l'écran et ajoute uniquement des marqueurs de log peu bruyants.
    /// </summary>
    public static class HumanSmokeTestMode
    {
        public const string CommandLineFlag = "--human-test";

        private static readonly bool Enabled = ContainsFlag(Environment.GetCommandLineArgs());
        private static readonly HashSet<string> LoggedEventKeys = new(StringComparer.Ordinal);

        public static bool IsEnabled => Enabled;

        public static bool ContainsFlag(string[] arguments)
        {
            if (arguments == null)
                return false;

            foreach (var argument in arguments)
            {
                if (string.Equals(argument, CommandLineFlag, StringComparison.OrdinalIgnoreCase))
                    return true;
            }

            return false;
        }

        public static void LogEvent(string eventName, string details = null)
        {
            if (!Enabled)
                return;

            var suffix = string.IsNullOrWhiteSpace(details) ? string.Empty : $" {details}";
            Debug.Log($"[GAME-SMOKE] {eventName}{suffix}");
        }

        /// <summary>
        /// Écrit une étape de diagnostic une seule fois par processus. Les interactions
        /// répétées chaque frame restent ainsi observables sans noyer le log.
        /// </summary>
        public static void LogEventOnce(string key, string eventName, string details = null)
        {
            if (!Enabled || string.IsNullOrWhiteSpace(key) || !LoggedEventKeys.Add(key))
                return;

            LogEvent(eventName, details);
        }
    }
}
