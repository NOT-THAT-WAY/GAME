using System.Collections;
using NotThatWay.Game.Input;
using NotThatWay.Game.PlayerSimulation;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.TestTools;
#if UNITY_EDITOR
using UnityEditor;
#endif

namespace NotThatWay.Game.Tests.PlayMode
{
    public sealed class PlayerInputSourcePlayModeTests : InputTestFixture
    {
        [UnityTest]
        public IEnumerator DisableReenable_ResetsEdgesAndDoesNotDoubleSubscribe()
        {
#if !UNITY_EDITOR
            Assert.Ignore("Le test de l'asset projet nécessite l'AssetDatabase de l'Editor.");
            yield break;
#else
            var asset = AssetDatabase.LoadAssetAtPath<InputActionAsset>(
                "Assets/_Project/Input/GameControls.inputactions");
            Assert.That(asset, Is.Not.Null);

            var keyboard = InputSystem.AddDevice<Keyboard>();
            var mouse = InputSystem.AddDevice<Mouse>();
            var gameObject = new GameObject("Player input lifecycle test");
            gameObject.SetActive(false);
            var source = gameObject.AddComponent<PlayerInputSource>();
            source.Configure(asset);
            source.RestrictToDevices(keyboard, mouse);
            gameObject.SetActive(true);
            Assert.That(source.IsReady, Is.True);

            Press(keyboard.spaceKey);
            yield return null;
            source.enabled = false;
            Assert.That(source.IsReady, Is.False);

            Release(keyboard.spaceKey);
            yield return null;
            source.enabled = true;
            Assert.That(source.IsReady, Is.True);
            Assert.That(source.ConsumeCommand(1u, 1f / 60f)
                .Has(PlayerCommandButtons.JumpPressed), Is.False);

            Press(keyboard.spaceKey);
            yield return null;
            Assert.That(source.ConsumeCommand(2u, 1f / 60f)
                .Has(PlayerCommandButtons.JumpPressed), Is.True);
            Assert.That(source.ConsumeCommand(3u, 1f / 60f)
                .Has(PlayerCommandButtons.JumpPressed), Is.False);

            Object.Destroy(gameObject);
            yield return null;
#endif
        }
    }
}
