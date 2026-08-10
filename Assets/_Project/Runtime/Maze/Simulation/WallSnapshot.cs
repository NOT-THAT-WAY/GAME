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
    /// Snapshot autonome d'un battant : le segment de mouvement en cours, jamais un
    /// transform. Son codec binaire est explicitement versionné, little-endian via
    /// BinaryWriter, et n'encode aucun flottant ni ID dense.
    /// </summary>
    public readonly struct WallSnapshot : IEquatable<WallSnapshot>
    {
        public const byte FormatVersion = 2;

        public WallSnapshot(WallState state)
        {
            if (state.WallId <= 0)
                throw new ArgumentException("État de mur non initialisé.", nameof(state));

            WallId = state.WallId;
            AngleMilliDegrees = state.AngleMilliDegrees;
            AngularVelocityMilliDegreesPerTick = state.AngularVelocityMilliDegreesPerTick;
            AnchorTick = state.AnchorTick;
            Revision = state.Revision;
        }

        public int WallId { get; }
        public int AngleMilliDegrees { get; }
        public int AngularVelocityMilliDegreesPerTick { get; }
        public uint AnchorTick { get; }
        public uint Revision { get; }
        public bool IsRotating => AngularVelocityMilliDegreesPerTick != 0;

        /// <summary>
        /// L'ancrage du segment est aussi le tick de capture : l'historique client
        /// n'a pas besoin d'une seconde horloge pour replacer la pose.
        /// </summary>
        public uint CapturedTick => AnchorTick;

        public byte[] ToBytes()
        {
            using var stream = new MemoryStream(24);
            using var writer = new BinaryWriter(stream);
            writer.Write(FormatVersion);
            writer.Write(WallId);
            writer.Write(AngleMilliDegrees);
            writer.Write(AngularVelocityMilliDegreesPerTick);
            writer.Write(AnchorTick);
            writer.Write(Revision);
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
                var angleMilliDegrees = reader.ReadInt32();
                var angularVelocity = reader.ReadInt32();
                var anchorTick = reader.ReadUInt32();
                var revision = reader.ReadUInt32();
                if (stream.Position != stream.Length)
                {
                    rejectionCode = WallSnapshotDecodeCodes.PayloadTrailingBytes;
                    return false;
                }

                snapshot = new WallSnapshot(new WallState(
                    wallId,
                    angleMilliDegrees,
                    angularVelocity,
                    anchorTick,
                    revision));
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

        internal WallState ToWallState() => new(
            WallId,
            AngleMilliDegrees,
            AngularVelocityMilliDegreesPerTick,
            AnchorTick,
            Revision);

        public bool Equals(WallSnapshot other) =>
            WallId == other.WallId &&
            AngleMilliDegrees == other.AngleMilliDegrees &&
            AngularVelocityMilliDegreesPerTick == other.AngularVelocityMilliDegreesPerTick &&
            AnchorTick == other.AnchorTick &&
            Revision == other.Revision;

        public override bool Equals(object value) => value is WallSnapshot other && Equals(other);

        public override int GetHashCode() => HashCode.Combine(
            WallId, AngleMilliDegrees, AngularVelocityMilliDegreesPerTick, AnchorTick, Revision);
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
