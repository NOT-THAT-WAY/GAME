using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class EditModeSmokeTests
    {
        [Test]
        public void RuntimeAssembly_IsReachableAndVersioned()
        {
            Assert.That(GameVersion.Current, Is.Not.Null.And.Not.Empty);
        }

        [Test]
        public void BuildIdentity_ValidRecordFormatsStableMarker()
        {
            var identity = ValidBuildIdentity();

            Assert.That(BuildIdentity.Validate(identity, out var error), Is.True, error);
            Assert.That(
                BuildIdentity.FormatMarker(identity),
                Is.EqualTo(
                    "[GAME-BUILD] schema=1 " +
                    $"buildId={new string('a', 64)} " +
                    $"buildSetId={new string('b', 64)} " +
                    $"commit={new string('c', 40)} dirty=false profile=connection " +
                    "platform=macos unity=6000.3.20f1 startedAt=2026-08-09T10:00:00Z"));
        }

        [Test]
        public void BuildIdentity_RejectsUnknownCommitClaimedAsClean()
        {
            var identity = ValidBuildIdentity();
            identity.sourceGitCommit = "unknown";

            Assert.That(BuildIdentity.Validate(identity, out var error), Is.False);
            Assert.That(error, Is.EqualTo("source_commit_invalid"));
        }

        [Test]
        public void BuildIdentity_RejectsMalformedIdentifier()
        {
            var identity = ValidBuildIdentity();
            identity.buildId = "not-a-sha256";

            Assert.That(BuildIdentity.Validate(identity, out var error), Is.False);
            Assert.That(error, Is.EqualTo("build_id_invalid"));
        }

        [Test]
        public void HumanTestFlag_ReturnsFalseWhenArgumentsAreNull()
        {
            Assert.That(HumanSmokeTestMode.ContainsFlag(null), Is.False);
        }

        [Test]
        public void HumanTestFlag_ReturnsFalseWhenFlagIsAbsent()
        {
            Assert.That(
                HumanSmokeTestMode.ContainsFlag(new[] { "GAME", "--game-role", "host" }),
                Is.False);
        }

        [Test]
        public void HumanTestFlag_ReturnsTrueWhenFlagIsPresent()
        {
            Assert.That(
                HumanSmokeTestMode.ContainsFlag(new[] { "GAME", "--human-test" }),
                Is.True);
        }

        [Test]
        public void HumanTestFlag_IsCaseInsensitive()
        {
            Assert.That(
                HumanSmokeTestMode.ContainsFlag(new[] { "--HUMAN-TEST" }),
                Is.True);
        }

        private static BuildIdentityRecord ValidBuildIdentity()
        {
            return new BuildIdentityRecord
            {
                schemaVersion = BuildIdentity.CurrentSchemaVersion,
                buildId = new string('a', 64),
                buildSetId = new string('b', 64),
                sourceGitCommit = new string('c', 40),
                sourceDirtyWorktree = false,
                profile = "connection",
                platform = "macos",
                unityVersion = "6000.3.20f1",
                startedAtUtc = "2026-08-09T10:00:00Z"
            };
        }
    }
}
