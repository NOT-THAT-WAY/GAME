using System;
using System.Text;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class FishNetVersionHandshakeGuardTests
    {
        private const int PrefixLength = 3;
        private const int MarkerIndex = PrefixLength + 6;

        [Test]
        public void Normalize_LeavesValidVersionPacketUnchanged()
        {
            var bytes = CreatePacket(0x0A);
            var packet = new ArraySegment<byte>(bytes, PrefixLength, 12);

            var status = FishNetVersionPacketGuard.Normalize(packet, out var observed);

            Assert.That(status, Is.EqualTo(FishNetVersionPacketStatus.Valid));
            Assert.That(observed, Is.EqualTo(0x0A));
            Assert.That(bytes[MarkerIndex], Is.EqualTo(0x0A));
        }

        [Test]
        public void Normalize_RepairsExactNegativeLengthMarker()
        {
            var bytes = CreatePacket(0x0B);
            var packet = new ArraySegment<byte>(bytes, PrefixLength, 12);

            var status = FishNetVersionPacketGuard.Normalize(packet, out var observed);

            Assert.That(status, Is.EqualTo(FishNetVersionPacketStatus.CorrectedMalformedLength));
            Assert.That(observed, Is.EqualTo(0x0B));
            Assert.That(bytes[MarkerIndex], Is.EqualTo(0x0A));
        }

        [Test]
        public void Normalize_DoesNotRewriteDifferentFishNetVersion()
        {
            var bytes = CreatePacket(0x0B, "4.7.3");
            var packet = new ArraySegment<byte>(bytes, PrefixLength, 12);

            var status = FishNetVersionPacketGuard.Normalize(packet, out _);

            Assert.That(status, Is.EqualTo(FishNetVersionPacketStatus.NotVersionPacket));
            Assert.That(bytes[MarkerIndex], Is.EqualTo(0x0B));
        }

        [Test]
        public void Normalize_DoesNotRewriteAnotherPacketType()
        {
            var bytes = CreatePacket(0x0B);
            bytes[PrefixLength + 4] = 20;
            var packet = new ArraySegment<byte>(bytes, PrefixLength, 12);

            var status = FishNetVersionPacketGuard.Normalize(packet, out _);

            Assert.That(status, Is.EqualTo(FishNetVersionPacketStatus.NotVersionPacket));
            Assert.That(bytes[MarkerIndex], Is.EqualTo(0x0B));
        }

        [Test]
        public void Normalize_ReportsUnknownMarkerWithoutWeakeningVersionCheck()
        {
            var bytes = CreatePacket(0x09);
            var packet = new ArraySegment<byte>(bytes, PrefixLength, 12);

            var status = FishNetVersionPacketGuard.Normalize(packet, out var observed);

            Assert.That(status, Is.EqualTo(FishNetVersionPacketStatus.UnsupportedMalformedLength));
            Assert.That(observed, Is.EqualTo(0x09));
            Assert.That(bytes[MarkerIndex], Is.EqualTo(0x09));
        }

        private static byte[] CreatePacket(byte marker, string version = "4.7.2")
        {
            var result = new byte[PrefixLength + 12 + 2];
            var offset = PrefixLength;
            result[offset] = 0x78;
            result[offset + 1] = 0x56;
            result[offset + 2] = 0x34;
            result[offset + 3] = 0x12;
            result[offset + 4] = 21;
            result[offset + 5] = 0;
            result[offset + 6] = marker;
            Encoding.UTF8.GetBytes(version, 0, version.Length, result, offset + 7);
            return result;
        }
    }
}
