using System;
using System.IO;

namespace NotThatWay.Game.Simulation
{
    public static class WallSnapshotDecodeCodes
    {
        public const string None = "none";
        public const string PayloadMissing = "payload_missing";
        public const string FormatUnsupported = "format_unsupported";
        public const string PayloadMalformed = "payload_malformed";
        public const string PayloadTrailingBytes = "payload_trailing_bytes";
    }

    /// <summary>
    /// Snapshot autonome d'un mur. Son codec binaire est explicitement versionné,
    /// little-endian via BinaryWriter et n'encode aucun flottant ni ID dense.
    /// </summary>
    public readonly struct WallSnapshot : IEquatable<WallSnapshot>
    {
        public const byte FormatVersion = 1;

        public WallSnapshot(WallState state, uint capturedTick)
        {
            if (state.WallId <= 0)
                throw new ArgumentException("État de mur non initialisé.", nameof(state));
            if (state.ActiveTransition.HasValue)
            {
                var transition = state.ActiveTransition.Value;
                if (TickMath.IsOlder(capturedTick, transition.StartTick) || transition.IsComplete(capturedTick))
                {
                    throw new ArgumentException(
                        "Un snapshot actif doit être capturé pendant sa transition.",
                        nameof(capturedTick));
                }
            }

            WallId = state.WallId;
            StateId = state.StateId;
            Revision = state.Revision;
            CapturedTick = capturedTick;
            SignedEffort = state.SignedEffort;
            ActiveTransition = state.ActiveTransition;
        }

        public int WallId { get; }
        public int StateId { get; }
        public uint Revision { get; }
        public uint CapturedTick { get; }
        public int SignedEffort { get; }
        public WallTransition? ActiveTransition { get; }
        public bool IsTransitioning => ActiveTransition.HasValue;

        public byte[] ToBytes()
        {
            using var stream = new MemoryStream(48);
            using var writer = new BinaryWriter(stream);
            writer.Write(FormatVersion);
            writer.Write(WallId);
            writer.Write(StateId);
            writer.Write(Revision);
            writer.Write(CapturedTick);
            writer.Write(SignedEffort);
            writer.Write((byte)(ActiveTransition.HasValue ? 1 : 0));
            if (ActiveTransition.HasValue)
            {
                var transition = ActiveTransition.Value;
                writer.Write(transition.WallId);
                writer.Write(transition.FromStateId);
                writer.Write(transition.ToStateId);
                writer.Write(transition.StartTick);
                writer.Write(transition.DurationTicks);
                writer.Write(transition.Revision);
            }
            writer.Flush();
            return stream.ToArray();
        }

        public static bool TryFromBytes(
            byte[] payload,
            out WallSnapshot snapshot,
            out string rejectionCode)
        {
            snapshot = default;
            if (payload == null || payload.Length == 0)
            {
                rejectionCode = WallSnapshotDecodeCodes.PayloadMissing;
                return false;
            }

            try
            {
                using var stream = new MemoryStream(payload, false);
                using var reader = new BinaryReader(stream);
                if (reader.ReadByte() != FormatVersion)
                {
                    rejectionCode = WallSnapshotDecodeCodes.FormatUnsupported;
                    return false;
                }

                var wallId = reader.ReadInt32();
                var stateId = reader.ReadInt32();
                var revision = reader.ReadUInt32();
                var capturedTick = reader.ReadUInt32();
                var signedEffort = reader.ReadInt32();
                var transitionFlag = reader.ReadByte();
                if (transitionFlag > 1)
                {
                    rejectionCode = WallSnapshotDecodeCodes.PayloadMalformed;
                    return false;
                }

                WallTransition? transition = null;
                if (transitionFlag == 1)
                {
                    transition = new WallTransition(
                        reader.ReadInt32(),
                        reader.ReadInt32(),
                        reader.ReadInt32(),
                        reader.ReadUInt32(),
                        reader.ReadUInt32(),
                        reader.ReadUInt32());
                }

                if (stream.Position != stream.Length)
                {
                    rejectionCode = WallSnapshotDecodeCodes.PayloadTrailingBytes;
                    return false;
                }

                snapshot = new WallSnapshot(
                    new WallState(wallId, stateId, revision, signedEffort, transition),
                    capturedTick);
                rejectionCode = WallSnapshotDecodeCodes.None;
                return true;
            }
            catch (Exception exception) when (
                exception is EndOfStreamException ||
                exception is IOException ||
                exception is ArgumentException ||
                exception is OverflowException)
            {
                rejectionCode = WallSnapshotDecodeCodes.PayloadMalformed;
                snapshot = default;
                return false;
            }
        }

        internal WallState ToWallState() =>
            new(WallId, StateId, Revision, SignedEffort, ActiveTransition);

        public bool Equals(WallSnapshot other) =>
            WallId == other.WallId &&
            StateId == other.StateId &&
            Revision == other.Revision &&
            CapturedTick == other.CapturedTick &&
            SignedEffort == other.SignedEffort &&
            Nullable.Equals(ActiveTransition, other.ActiveTransition);

        public override bool Equals(object value) => value is WallSnapshot other && Equals(other);
        public override int GetHashCode() => HashCode.Combine(
            WallId, StateId, Revision, CapturedTick, SignedEffort, ActiveTransition);
    }

    public enum WallSnapshotApplyStatus : byte
    {
        Applied = 0,
        Duplicate = 1,
        Stale = 2,
        RevisionConflict = 3,
        Invalid = 4
    }
}
