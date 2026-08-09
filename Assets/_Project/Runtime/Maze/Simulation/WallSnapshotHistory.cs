using System;

namespace NotThatWay.Game.Simulation
{
    public static class WallSnapshotReceiverPolicy
    {
        private const int PredictionWindowSeconds = 5;
        private const int SafetyMarginTicks = 64;

        public static bool ShouldProcess(bool isServerStarted) => !isServerStarted;

        public static int CalculateHistoryCapacity(ushort tickRate)
        {
            return checked(tickRate * PredictionWindowSeconds + SafetyMarginTicks);
        }

        public static bool ShouldBroadcast(bool stateChanged, uint logicalTick, ushort tickRate)
        {
            if (tickRate == 0)
                throw new ArgumentOutOfRangeException(nameof(tickRate));
            return stateChanged || logicalTick % tickRate == 0u;
        }

        public static ulong ComputeSimulationFingerprint(
            WallSimulationSettings settings,
            int effortPerHeldTick,
            int reachFromCapsuleMm)
        {
            settings.Validate();
            if (effortPerHeldTick <= 0 || reachFromCapsuleMm < 0)
                throw new ArgumentOutOfRangeException(nameof(effortPerHeldTick));

            const ulong offset = 14695981039346656037UL;
            const ulong prime = 1099511628211UL;
            var hash = offset;
            Add(unchecked((uint)settings.EffortThreshold));
            Add(unchecked((uint)settings.MaximumEffortPerSourcePerTick));
            Add(unchecked((uint)settings.EffortDecayPerTick));
            Add(unchecked((uint)settings.RejectedEffortRetention));
            Add(settings.TransitionDurationTicks);
            Add(unchecked((uint)effortPerHeldTick));
            Add(unchecked((uint)reachFromCapsuleMm));
            return hash;

            void Add(uint value)
            {
                for (var shift = 0; shift < 32; shift += 8)
                {
                    hash ^= (byte)(value >> shift);
                    hash *= prime;
                }
            }
        }
    }

    /// <summary>
    /// Horloge de rendu live : elle suit l'estimation serveur FishNet lorsqu'elle
    /// avance, mais ne recule jamais. Les ticks historiques de replay restent séparés.
    /// </summary>
    public sealed class WallLiveTickClock
    {
        public bool IsInitialized { get; private set; }
        public uint Tick { get; private set; }

        public bool TryPreviewObservation(
            uint snapshotTick,
            uint estimatedServerTick,
            out uint candidate)
        {
            if (!TryLater(snapshotTick, estimatedServerTick, out candidate))
                return false;
            if (!IsInitialized)
                return true;
            return TryLater(Tick, candidate, out candidate);
        }

        public void CommitObservation(uint candidate)
        {
            if (IsInitialized)
            {
                int order;
                try
                {
                    order = TickMath.Compare(candidate, Tick);
                }
                catch (ArgumentException exception)
                {
                    throw new InvalidOperationException(
                        "Commit ambigu de l'horloge murale live.", exception);
                }
                if (order < 0)
                    throw new InvalidOperationException("L'horloge murale live ne peut pas reculer.");
            }
            Tick = candidate;
            IsInitialized = true;
        }

        public void Reset()
        {
            Tick = 0u;
            IsInitialized = false;
        }

        private static bool TryLater(uint left, uint right, out uint later)
        {
            int order;
            try
            {
                order = TickMath.Compare(right, left);
            }
            catch (ArgumentException)
            {
                later = default;
                return false;
            }
            later = order > 0 ? right : left;
            return true;
        }
    }

    public enum WallSnapshotRecordStatus : byte
    {
        Added = 0,
        Duplicate = 1,
        Stale = 2,
        Conflict = 3,
        Invalid = 4
    }

    public readonly struct WallSnapshotTimelineSample
    {
        public WallSnapshotTimelineSample(uint serverTransportTick, WallSnapshot snapshot)
        {
            if (snapshot.WallId <= 0)
                throw new ArgumentException("Snapshot non initialisé.", nameof(snapshot));
            ServerTransportTick = serverTransportTick;
            Snapshot = snapshot;
        }

        public uint ServerTransportTick { get; }
        public WallSnapshot Snapshot { get; }

        public uint ProjectLogicalTick(uint targetServerTransportTick)
        {
            if (TickMath.IsOlder(targetServerTransportTick, ServerTransportTick))
                return Snapshot.CapturedTick;
            var elapsed = unchecked(targetServerTransportTick - ServerTransportTick);
            return unchecked(Snapshot.CapturedTick + elapsed);
        }
    }

    /// <summary>
    /// Anneau chronologique sans allocation utilisé pour replacer les murs avant
    /// chaque replay FishNet. Il conserve le tick transport séparé du tick logique.
    /// </summary>
    public sealed class WallSnapshotHistory
    {
        private readonly WallSnapshotTimelineSample[] _entries;
        private int _nextIndex;
        private int _count;
        private int _wallId;

        public WallSnapshotHistory(int capacity)
        {
            if (capacity <= 0)
                throw new ArgumentOutOfRangeException(nameof(capacity));
            _entries = new WallSnapshotTimelineSample[capacity];
        }

        public int Capacity => _entries.Length;
        public int Count => _count;

        public WallSnapshotRecordStatus PreviewRecord(
            uint serverTransportTick,
            WallSnapshot snapshot)
        {
            if (snapshot.WallId <= 0)
                return WallSnapshotRecordStatus.Invalid;
            if (_wallId != 0 && snapshot.WallId != _wallId)
                return WallSnapshotRecordStatus.Invalid;

            if (_count > 0)
            {
                var newest = Newest;
                int order;
                try
                {
                    order = TickMath.Compare(serverTransportTick, newest.ServerTransportTick);
                }
                catch (ArgumentException)
                {
                    return WallSnapshotRecordStatus.Invalid;
                }

                if (order < 0)
                    return WallSnapshotRecordStatus.Stale;
                if (order == 0)
                {
                    return snapshot.Equals(newest.Snapshot)
                        ? WallSnapshotRecordStatus.Duplicate
                        : WallSnapshotRecordStatus.Conflict;
                }
            }

            return WallSnapshotRecordStatus.Added;
        }

        public WallSnapshotRecordStatus Record(uint serverTransportTick, WallSnapshot snapshot)
        {
            var status = PreviewRecord(serverTransportTick, snapshot);
            if (status != WallSnapshotRecordStatus.Added)
                return status;

            _wallId = snapshot.WallId;
            _entries[_nextIndex] = new WallSnapshotTimelineSample(serverTransportTick, snapshot);
            _nextIndex = (_nextIndex + 1) % _entries.Length;
            if (_count < _entries.Length)
                _count++;
            return status;
        }

        public bool TryGetAtOrBefore(
            uint serverTransportTick,
            out WallSnapshotTimelineSample sample)
        {
            for (var offset = 0; offset < _count; offset++)
            {
                var index = (_nextIndex - 1 - offset + _entries.Length) % _entries.Length;
                var candidate = _entries[index];
                try
                {
                    if (!TickMath.IsNewer(candidate.ServerTransportTick, serverTransportTick))
                    {
                        sample = candidate;
                        return true;
                    }
                }
                catch (ArgumentException)
                {
                    // Une entrée ambiguë à 2^31 ne peut pas être une base sûre.
                }
            }

            sample = default;
            return false;
        }

        public bool TryGetNewest(out WallSnapshotTimelineSample sample)
        {
            if (_count == 0)
            {
                sample = default;
                return false;
            }
            sample = Newest;
            return true;
        }

        public bool TryGetOldest(out WallSnapshotTimelineSample sample)
        {
            if (_count == 0)
            {
                sample = default;
                return false;
            }
            var index = (_nextIndex - _count + _entries.Length) % _entries.Length;
            sample = _entries[index];
            return true;
        }

        public void Clear()
        {
            Array.Clear(_entries, 0, _entries.Length);
            _nextIndex = 0;
            _count = 0;
            _wallId = 0;
        }

        private WallSnapshotTimelineSample Newest =>
            _entries[(_nextIndex - 1 + _entries.Length) % _entries.Length];
    }
}
