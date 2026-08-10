using System.Collections;
using NotThatWay.Game.PlayerSimulation;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace NotThatWay.Game.Tests.PlayMode
{
    public sealed class UnityCharacterControllerWorldTests
    {
        [UnityTest]
        public IEnumerator Move_MapsGroundAndSideCollisionsAndSetPosePreservesEnabledState()
        {
            var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            var wall = GameObject.CreatePrimitive(PrimitiveType.Cube);
            var player = new GameObject("CharacterController adapter test");
            try
            {
                floor.transform.position = new Vector3(0f, -0.1f, 0f);
                floor.transform.localScale = new Vector3(8f, 0.2f, 8f);
                wall.transform.position = new Vector3(1f, 1f, 0f);
                wall.transform.localScale = new Vector3(0.2f, 2f, 3f);

                player.transform.position = new Vector3(0f, 0.05f, 0f);
                var controller = player.AddComponent<CharacterController>();
                controller.height = 1.8f;
                controller.radius = 0.4f;
                controller.center = new Vector3(0f, 0.9f, 0f);
                controller.skinWidth = 0.02f;
                var world = new UnityCharacterControllerWorld(controller);
                Physics.SyncTransforms();
                yield return null;

                var start = UnityCharacterControllerWorld.ToDomain(player.transform.position);
                var groundingRequest = new PlayerCollisionRequest(
                    1u,
                    start,
                    new PlayerVector3(0d, -0.5d, 0d),
                    9000,
                    1.8d,
                    0.4d);
                var grounding = world.Move(in groundingRequest);
                Assert.That(grounding.IsGrounded, Is.True);
                Assert.That(player.transform.eulerAngles.y, Is.EqualTo(90f).Within(0.001f));

                var sideRequest = new PlayerCollisionRequest(
                    2u,
                    grounding.ResolvedPosition,
                    new PlayerVector3(2d, -0.05d, 0d),
                    9000,
                    1.8d,
                    0.4d);
                var side = world.Move(in sideRequest);
                Assert.That(
                    (side.Flags & PlayerCollisionFlags.Sides) != 0,
                    Is.True,
                    "Le mur doit être renvoyé comme collision latérale.");
                Assert.That(side.ResolvedPosition.X, Is.LessThan(0.7d));

                world.SetPose(new PlayerVector3(-2d, 0.05d, 1d), 18000);
                Assert.That(controller.enabled, Is.True);
                Assert.That(player.transform.position, Is.EqualTo(new Vector3(-2f, 0.05f, 1f)));
                Assert.That(player.transform.eulerAngles.y, Is.EqualTo(180f).Within(0.001f));

                controller.enabled = false;
                world.SetPose(new PlayerVector3(2d, 0.05d, -1d), 0);
                Assert.That(controller.enabled, Is.False);
                Assert.That(player.transform.position, Is.EqualTo(new Vector3(2f, 0.05f, -1f)));
            }
            finally
            {
                Object.DestroyImmediate(player);
                Object.DestroyImmediate(wall);
                Object.DestroyImmediate(floor);
            }
        }
    }
}
