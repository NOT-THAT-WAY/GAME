using System;
using System.Text;
using FishNet.Managing;
using FishNet.Managing.Transporting;
using FishNet.Transporting;
using UnityEngine;

namespace NotThatWay.Game
{
    internal enum FishNetVersionPacketStatus
    {
        NotVersionPacket,
        Valid,
        CorrectedMalformedLength,
        UnsupportedMalformedLength
    }

    internal static class FishNetVersionPacketGuard
    {
        private const int LengthMarkerBytes = 1;
        private static readonly byte[] ExpectedVersionBytes =
            Encoding.UTF8.GetBytes(NetworkManager.FISHNET_VERSION);

        internal static FishNetVersionPacketStatus Normalize(
            ArraySegment<byte> packet,
            out byte observedLengthMarker)
        {
            observedLengthMarker = 0;
            if (packet.Array == null || ExpectedVersionBytes.Length > 63)
                return FishNetVersionPacketStatus.NotVersionPacket;

            var packetIdOffset = packet.Offset + TransportManager.UNPACKED_TICK_LENGTH;
            var lengthMarkerOffset = packetIdOffset + TransportManager.PACKETID_LENGTH;
            var payloadOffset = lengthMarkerOffset + LengthMarkerBytes;
            var expectedPacketLength =
                TransportManager.UNPACKED_TICK_LENGTH +
                TransportManager.PACKETID_LENGTH +
                LengthMarkerBytes +
                ExpectedVersionBytes.Length;

            // The version is the client's first and only FishNet message in this
            // bundle. Requiring the exact size prevents this compatibility guard
            // from accepting a different version which merely shares a prefix.
            if (packet.Count != expectedPacketLength)
                return FishNetVersionPacketStatus.NotVersionPacket;

            var data = packet.Array;
            var packetId = (ushort)(data[packetIdOffset] | data[packetIdOffset + 1] << 8);
            if (packetId != (ushort)PacketId.Version)
                return FishNetVersionPacketStatus.NotVersionPacket;

            for (var index = 0; index < ExpectedVersionBytes.Length; index++)
            {
                if (data[payloadOffset + index] != ExpectedVersionBytes[index])
                    return FishNetVersionPacketStatus.NotVersionPacket;
            }

            observedLengthMarker = data[lengthMarkerOffset];
            var expectedLengthMarker = (byte)(ExpectedVersionBytes.Length << 1);
            if (observedLengthMarker == expectedLengthMarker)
                return FishNetVersionPacketStatus.Valid;

            // Windows IL2CPP has produced 0x0B for the five-byte version string.
            // FishNet zig-zag decodes that marker as -6 and rejects the host's own
            // client. Only repair this exact one-bit corruption and exact payload.
            if (observedLengthMarker == (byte)(expectedLengthMarker | 1))
            {
                data[lengthMarkerOffset] = expectedLengthMarker;
                return FishNetVersionPacketStatus.CorrectedMalformedLength;
            }

            return FishNetVersionPacketStatus.UnsupportedMalformedLength;
        }

        internal static byte ExpectedLengthMarker => (byte)(ExpectedVersionBytes.Length << 1);
    }

    /// <summary>
    /// Narrow compatibility layer for the FishNet 4.7.2 version packet observed
    /// malformed in Windows IL2CPP players. It preserves FishNet's version check:
    /// only the exact compiled version payload may have its sign bit corrected.
    /// </summary>
    public sealed class FishNetVersionHandshakeGuard : IntermediateLayer
    {
        private bool _loggedIncomingValid;
        private bool _loggedOutgoingValid;

        public override ArraySegment<byte> HandleIncoming(ArraySegment<byte> src, bool fromServer)
        {
            if (!fromServer)
                Inspect(src, "server-incoming", ref _loggedIncomingValid);
            return src;
        }

        public override ArraySegment<byte> HandleOutgoing(ArraySegment<byte> src, bool toServer)
        {
            if (toServer)
                Inspect(src, "client-outgoing", ref _loggedOutgoingValid);
            return src;
        }

        private static string RuntimeBackend
        {
            get
            {
                #if ENABLE_IL2CPP
                return "il2cpp";
                #else
                return "mono";
                #endif
            }
        }

        private static void Inspect(
            ArraySegment<byte> packet,
            string stage,
            ref bool loggedValid)
        {
            var status = FishNetVersionPacketGuard.Normalize(packet, out var observedMarker);
            switch (status)
            {
                case FishNetVersionPacketStatus.CorrectedMalformedLength:
                    Debug.LogWarning(
                        $"[GAME-FISHNET-HANDSHAKE] repaired backend={RuntimeBackend} " +
                        $"stage={stage} observed=0x{observedMarker:X2} " +
                        $"expected=0x{FishNetVersionPacketGuard.ExpectedLengthMarker:X2} " +
                        $"packet={FormatPacket(packet)}");
                    break;
                case FishNetVersionPacketStatus.UnsupportedMalformedLength:
                    Debug.LogError(
                        $"[GAME-FISHNET-HANDSHAKE] unsupported backend={RuntimeBackend} " +
                        $"stage={stage} observed=0x{observedMarker:X2} " +
                        $"expected=0x{FishNetVersionPacketGuard.ExpectedLengthMarker:X2} " +
                        $"packet={FormatPacket(packet)}");
                    break;
                case FishNetVersionPacketStatus.Valid:
                    LogValidOnce(packet, stage, ref loggedValid);
                    break;
            }
        }

        private static string FormatPacket(ArraySegment<byte> packet)
        {
            return packet.Array == null
                ? "null"
                : BitConverter.ToString(packet.Array, packet.Offset, packet.Count);
        }

        private static void LogValidOnce(
            ArraySegment<byte> packet,
            string stage,
            ref bool logged)
        {
            #if UNITY_EDITOR || DEVELOPMENT_BUILD
            if (logged)
                return;

            logged = true;
            Debug.Log(
                $"[GAME-FISHNET-HANDSHAKE] valid backend={RuntimeBackend} " +
                $"stage={stage} marker=0x{FishNetVersionPacketGuard.ExpectedLengthMarker:X2} " +
                $"packet={FormatPacket(packet)}");
            #endif
        }
    }
}
