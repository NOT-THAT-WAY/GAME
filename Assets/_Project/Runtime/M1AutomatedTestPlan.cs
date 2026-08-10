using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NotThatWay.Game
{
    public readonly struct M1AutomatedTestObservation
    {
        public M1AutomatedTestObservation(
            bool authenticated,
            int playerCount,
            int serverConnectionCount,
            bool hasWall,
            int wallAngleMilliDegrees,
            uint wallRevision,
            int angularVelocityMilliDegreesPerTick,
            long cumulativeRotationMilliDegrees,
            uint quarterTurns,
            uint reversals,
            uint opposedTicks,
            uint sweptPushes,
            uint snapshots,
            uint targetSnapshots,
            uint observerSnapshots,
            uint invalidSnapshots,
            uint historyMisses)
        {
            Authenticated = authenticated;
            PlayerCount = playerCount;
            ServerConnectionCount = serverConnectionCount;
            HasWall = hasWall;
            WallAngleMilliDegrees = wallAngleMilliDegrees;
            WallRevision = wallRevision;
            AngularVelocityMilliDegreesPerTick = angularVelocityMilliDegreesPerTick;
            CumulativeRotationMilliDegrees = cumulativeRotationMilliDegrees;
            QuarterTurns = quarterTurns;
            Reversals = reversals;
            OpposedTicks = opposedTicks;
            SweptPushes = sweptPushes;
            Snapshots = snapshots;
            TargetSnapshots = targetSnapshots;
            ObserverSnapshots = observerSnapshots;
            InvalidSnapshots = invalidSnapshots;
            HistoryMisses = historyMisses;
        }

        public bool Authenticated { get; }
        public int PlayerCount { get; }
        public int ServerConnectionCount { get; }
        public bool HasWall { get; }
        public int WallAngleMilliDegrees { get; }
        public uint WallRevision { get; }
        public int AngularVelocityMilliDegreesPerTick { get; }

        /// <summary>Rotation signée accumulée depuis le démarrage de l'autorité.</summary>
        public long CumulativeRotationMilliDegrees { get; }

        public uint QuarterTurns { get; }
        public uint Reversals { get; }
        public uint OpposedTicks { get; }
        public uint SweptPushes { get; }
        public uint Snapshots { get; }
        public uint TargetSnapshots { get; }
        public uint ObserverSnapshots { get; }
        public uint InvalidSnapshots { get; }
        public uint HistoryMisses { get; }

        public long AbsoluteRotationMilliDegrees => Math.Abs(CumulativeRotationMilliDegrees);
    }

    /// <summary>Contrat de verdict pour les scénarios M1 lancés en deux processus.</summary>
    public readonly struct M1AutomatedTestPlan
    {
        private M1AutomatedTestPlan(
            string name,
            string runId,
            double evaluateAfterReadySeconds,
            double quitAfterSeconds,
            double readinessTimeoutSeconds,
            int expectedPlayers,
            int expectedServerConnections,
            long minimumRotationMilliDegrees,
            long maximumRotationMilliDegrees,
            long minimumRevision,
            uint minimumQuarterTurns,
            uint minimumReversals,
            uint minimumOpposedTicks,
            uint minimumSweptPushes,
            uint minimumSnapshots,
            uint minimumTargetSnapshots)
        {
            Name = name;
            RunId = runId;
            EvaluateAfterReadySeconds = evaluateAfterReadySeconds;
            QuitAfterSeconds = quitAfterSeconds;
            ReadinessTimeoutSeconds = readinessTimeoutSeconds;
            ExpectedPlayers = expectedPlayers;
            ExpectedServerConnections = expectedServerConnections;
            MinimumRotationMilliDegrees = minimumRotationMilliDegrees;
            MaximumRotationMilliDegrees = maximumRotationMilliDegrees;
            MinimumRevision = minimumRevision;
            MinimumQuarterTurns = minimumQuarterTurns;
            MinimumReversals = minimumReversals;
            MinimumOpposedTicks = minimumOpposedTicks;
            MinimumSweptPushes = minimumSweptPushes;
            MinimumSnapshots = minimumSnapshots;
            MinimumTargetSnapshots = minimumTargetSnapshots;
        }

        public string Name { get; }
        public string RunId { get; }
        public double EvaluateAfterReadySeconds { get; }
        public double QuitAfterSeconds { get; }
        public double ReadinessTimeoutSeconds { get; }
        public int ExpectedPlayers { get; }
        public int ExpectedServerConnections { get; }
        public long MinimumRotationMilliDegrees { get; }
        public long MaximumRotationMilliDegrees { get; }
        public long MinimumRevision { get; }
        public uint MinimumQuarterTurns { get; }
        public uint MinimumReversals { get; }
        public uint MinimumOpposedTicks { get; }
        public uint MinimumSweptPushes { get; }
        public uint MinimumSnapshots { get; }
        public uint MinimumTargetSnapshots { get; }
        public bool Enabled => QuitAfterSeconds > 0d;

        public bool IsReadyToArm(M1AutomatedTestObservation observation)
        {
            if (!observation.Authenticated || !observation.HasWall)
                return false;
            if (ExpectedPlayers >= 0 && observation.PlayerCount != ExpectedPlayers)
                return false;
            if (ExpectedServerConnections >= 0 &&
                observation.ServerConnectionCount != ExpectedServerConnections)
            {
                return false;
            }
            return true;
        }

        public static bool TryParse(
            IReadOnlyList<string> arguments,
            out M1AutomatedTestPlan plan,
            out string error)
        {
            plan = default;
            error = string.Empty;
            if (arguments == null)
            {
                error = "arguments_null";
                return false;
            }

            var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            var keys = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            {
                "--m1-test-name",
                "--m1-run-id",
                "--m1-evaluate-after-ready-seconds",
                "--m1-auto-quit-seconds",
                "--m1-readiness-timeout-seconds",
                "--m1-expect-players",
                "--m1-expect-connections",
                "--m1-expect-rotation-min-mdeg",
                "--m1-expect-rotation-max-mdeg",
                "--m1-expect-revision-min",
                "--m1-expect-quarter-turns-min",
                "--m1-expect-reversals-min",
                "--m1-expect-opposed-ticks-min",
                "--m1-expect-swept-pushes-min",
                "--m1-expect-snapshots-min",
                "--m1-expect-target-snapshots-min"
            };
            for (var index = 0; index < arguments.Count; index++)
            {
                var argument = arguments[index] ?? string.Empty;
                string key = null;
                string value = null;
                var equalsIndex = argument.IndexOf('=');
                if (equalsIndex > 0)
                {
                    var candidate = argument.Substring(0, equalsIndex);
                    if (keys.Contains(candidate))
                    {
                        key = candidate;
                        value = argument.Substring(equalsIndex + 1);
                    }
                }
                else if (keys.Contains(argument))
                {
                    key = argument;
                    if (index + 1 >= arguments.Count)
                    {
                        error = $"value_missing:{key}";
                        return false;
                    }
                    value = arguments[++index];
                }

                if (key == null)
                    continue;
                if (values.ContainsKey(key))
                {
                    error = $"value_duplicate:{key}";
                    return false;
                }
                values.Add(key, value ?? string.Empty);
            }

            if (!values.TryGetValue("--m1-auto-quit-seconds", out var quitText))
            {
                if (values.Count == 0)
                    return true;
                error = "quit_seconds_required";
                return false;
            }
            if (!double.TryParse(
                    quitText,
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out var quitSeconds) ||
                quitSeconds < 1d || quitSeconds > 60d)
            {
                error = "quit_seconds_invalid";
                return false;
            }

            var evaluateText = ValueOr(
                values,
                "--m1-evaluate-after-ready-seconds",
                quitText);
            if (!double.TryParse(
                    evaluateText,
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out var evaluateSeconds) ||
                evaluateSeconds < 0.5d || evaluateSeconds > quitSeconds)
            {
                error = "evaluate_seconds_invalid";
                return false;
            }
            var timeoutText = ValueOr(values, "--m1-readiness-timeout-seconds", "10");
            if (!double.TryParse(
                    timeoutText,
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out var timeoutSeconds) ||
                timeoutSeconds < 2d || timeoutSeconds > 60d)
            {
                error = "readiness_timeout_invalid";
                return false;
            }

            var name = ValueOr(values, "--m1-test-name", "unnamed").Trim();
            if (name.Length == 0 || name.Length > 48)
            {
                error = "test_name_invalid";
                return false;
            }
            var runId = ValueOr(values, "--m1-run-id", name).Trim();
            if (runId.Length == 0 || runId.Length > 64)
            {
                error = "run_id_invalid";
                return false;
            }
            if (!TryInt(values, "--m1-expect-players", -1, out var players) ||
                players < -1 || players > 16)
            {
                error = "players_invalid";
                return false;
            }
            if (!TryInt(values, "--m1-expect-connections", -1, out var connections) ||
                connections < -1 || connections > 16)
            {
                error = "connections_invalid";
                return false;
            }

            const long maximumTurns = 100L * 360_000L;
            if (!TryLong(values, "--m1-expect-rotation-min-mdeg", -1L, out var rotationMinimum) ||
                rotationMinimum < -1L || rotationMinimum > maximumTurns)
            {
                error = "rotation_min_invalid";
                return false;
            }
            if (!TryLong(values, "--m1-expect-rotation-max-mdeg", -1L, out var rotationMaximum) ||
                rotationMaximum < -1L || rotationMaximum > maximumTurns)
            {
                error = "rotation_max_invalid";
                return false;
            }
            if (!TryLong(values, "--m1-expect-revision-min", -1L, out var revisionMinimum) ||
                revisionMinimum < -1L || revisionMinimum > uint.MaxValue)
            {
                error = "revision_min_invalid";
                return false;
            }
            if (!TryUint(values, "--m1-expect-quarter-turns-min", out var quarterTurns) ||
                !TryUint(values, "--m1-expect-reversals-min", out var reversals) ||
                !TryUint(values, "--m1-expect-opposed-ticks-min", out var opposed) ||
                !TryUint(values, "--m1-expect-swept-pushes-min", out var sweptPushes) ||
                !TryUint(values, "--m1-expect-snapshots-min", out var snapshots) ||
                !TryUint(values, "--m1-expect-target-snapshots-min", out var targetSnapshots))
            {
                error = "minimum_invalid";
                return false;
            }

            plan = new M1AutomatedTestPlan(
                name,
                runId,
                evaluateSeconds,
                quitSeconds,
                timeoutSeconds,
                players,
                connections,
                rotationMinimum,
                rotationMaximum,
                revisionMinimum,
                quarterTurns,
                reversals,
                opposed,
                sweptPushes,
                snapshots,
                targetSnapshots);
            return true;
        }

        public bool Evaluate(M1AutomatedTestObservation observation, out string reason)
        {
            var failures = new StringBuilder();
            AddFailure(!observation.Authenticated, "not_authenticated", failures);
            AddFailure(
                ExpectedPlayers >= 0 && observation.PlayerCount != ExpectedPlayers,
                $"players={observation.PlayerCount}!={ExpectedPlayers}",
                failures);
            AddFailure(
                ExpectedServerConnections >= 0 &&
                observation.ServerConnectionCount != ExpectedServerConnections,
                $"connections={observation.ServerConnectionCount}!={ExpectedServerConnections}",
                failures);

            var requiresWall = MinimumRotationMilliDegrees >= 0L ||
                               MaximumRotationMilliDegrees >= 0L ||
                               MinimumRevision >= 0L ||
                               MinimumQuarterTurns > 0u || MinimumReversals > 0u ||
                               MinimumOpposedTicks > 0u || MinimumSweptPushes > 0u;
            AddFailure(requiresWall && !observation.HasWall, "wall_unavailable", failures);
            AddFailure(
                MinimumRotationMilliDegrees >= 0L &&
                observation.AbsoluteRotationMilliDegrees < MinimumRotationMilliDegrees,
                $"rotation={observation.AbsoluteRotationMilliDegrees}<{MinimumRotationMilliDegrees}",
                failures);
            AddFailure(
                MaximumRotationMilliDegrees >= 0L &&
                observation.AbsoluteRotationMilliDegrees > MaximumRotationMilliDegrees,
                $"rotation={observation.AbsoluteRotationMilliDegrees}>{MaximumRotationMilliDegrees}",
                failures);
            AddFailure(
                MinimumRevision >= 0L && observation.WallRevision < (uint)MinimumRevision,
                $"revision={observation.WallRevision}<{MinimumRevision}",
                failures);
            AddFailure(
                observation.QuarterTurns < MinimumQuarterTurns,
                $"quarterTurns={observation.QuarterTurns}<{MinimumQuarterTurns}",
                failures);
            AddFailure(
                observation.Reversals < MinimumReversals,
                $"reversals={observation.Reversals}<{MinimumReversals}",
                failures);
            AddFailure(
                observation.OpposedTicks < MinimumOpposedTicks,
                $"opposedTicks={observation.OpposedTicks}<{MinimumOpposedTicks}",
                failures);
            AddFailure(
                observation.SweptPushes < MinimumSweptPushes,
                $"sweptPushes={observation.SweptPushes}<{MinimumSweptPushes}",
                failures);
            AddFailure(
                observation.Snapshots < MinimumSnapshots,
                $"snapshots={observation.Snapshots}<{MinimumSnapshots}",
                failures);
            AddFailure(
                observation.TargetSnapshots < MinimumTargetSnapshots,
                $"targetSnapshots={observation.TargetSnapshots}<{MinimumTargetSnapshots}",
                failures);
            AddFailure(observation.InvalidSnapshots != 0u,
                $"invalidSnapshots={observation.InvalidSnapshots}", failures);
            AddFailure(observation.HistoryMisses != 0u,
                $"historyMisses={observation.HistoryMisses}", failures);

            reason = failures.Length == 0 ? "ok" : failures.ToString();
            return failures.Length == 0;
        }

        private static string ValueOr(
            IReadOnlyDictionary<string, string> values,
            string key,
            string fallback) => values.TryGetValue(key, out var value) ? value : fallback;

        private static bool TryInt(
            IReadOnlyDictionary<string, string> values,
            string key,
            int fallback,
            out int value)
        {
            var text = ValueOr(values, key, fallback.ToString(CultureInfo.InvariantCulture));
            return int.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out value);
        }

        private static bool TryLong(
            IReadOnlyDictionary<string, string> values,
            string key,
            long fallback,
            out long value)
        {
            var text = ValueOr(values, key, fallback.ToString(CultureInfo.InvariantCulture));
            return long.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out value);
        }

        private static bool TryUint(
            IReadOnlyDictionary<string, string> values,
            string key,
            out uint value)
        {
            var text = ValueOr(values, key, "0");
            return uint.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out value);
        }

        private static void AddFailure(bool condition, string code, StringBuilder failures)
        {
            if (!condition)
                return;
            if (failures.Length > 0)
                failures.Append(';');
            failures.Append(code);
        }
    }
}
