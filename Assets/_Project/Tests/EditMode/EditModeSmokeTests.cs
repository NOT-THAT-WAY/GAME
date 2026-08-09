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
    }
}
