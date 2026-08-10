using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace NotThatWay.Game.Tests.PlayMode
{
    public sealed class PlayModeSmokeTests
    {
        [UnityTest]
        public IEnumerator TestRunner_EntersPlayModeAndAdvancesAFrame()
        {
            Assert.That(Application.isPlaying, Is.True);
            Assert.That(GameVersion.Current, Is.Not.Null.And.Not.Empty);

            var marker = new GameObject("PlayModeSmokeMarker");
            var startingFrame = Time.frameCount;

            try
            {
                yield return null;

                Assert.That(Time.frameCount, Is.GreaterThan(startingFrame));
                Assert.That(marker.activeInHierarchy, Is.True);
            }
            finally
            {
                Object.DestroyImmediate(marker);
            }
        }
    }
}
