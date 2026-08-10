using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace NotThatWay.Game.Tests.PlayMode
{
    /// <summary>
    /// M1PlayerAppearance est un NetworkBehaviour dont IsOwner exige un
    /// NetworkObject initialisé par un spawn FishNet — aucun test PlayMode du
    /// dépôt ne met ça en place (voir M1PunchTargeting, testé directement plus
    /// bas dans TopologyArenaPlayModeTests). Le bras à ressort est donc une
    /// classe pure et c'est elle qu'on teste ici, contre de vrais colliders,
    /// avec un simple Transform à la place du pivot caméra.
    /// </summary>
    public sealed class M1ThirdPersonSpringArmPlayModeTests
    {
        // Copie de M1PlayerAppearance.ThirdPersonCameraOffset : la longueur de
        // repos du bras (≈3,44 m) que la sonde ne doit jamais dépasser.
        private static readonly Vector3 RestLocalOffset = new(0f, 0.55f, -3.4f);

        [UnityTest]
        public IEnumerator Resolve_KeepsTheCameraInFrontOfAWallBehindThePlayerAcrossSeveralFrames()
        {
            var anchor = new GameObject("SpringArmAnchor");
            var wall = CreateWorldWall("WallBehindPlayer", new Vector3(0f, 1.05f, -2.6f), new Vector3(5f, 5f, 0.4f));
            try
            {
                anchor.transform.position = new Vector3(0f, 1.05f, 0f);
                Physics.SyncTransforms();

                var springArm = new M1ThirdPersonSpringArm();
                var worldMask = 1 << GameplayLayers.World;
                var restDistance = RestLocalOffset.magnitude;
                var lastDistance = 0f;

                for (var frame = 0; frame < 30; frame++)
                {
                    yield return null;
                    var localOffset = springArm.Resolve(anchor.transform, RestLocalOffset, Time.deltaTime);
                    lastDistance = localOffset.magnitude;

                    Assert.That(
                        lastDistance,
                        Is.GreaterThanOrEqualTo(M1ThirdPersonSpringArm.MinimumDistanceMeters - 0.0005f),
                        "Le bras ne doit jamais descendre sous la distance plancher.");
                    Assert.That(
                        lastDistance,
                        Is.LessThanOrEqualTo(restDistance + 0.0005f),
                        "Le bras ne doit jamais dépasser sa longueur de repos.");

                    // Le vrai test de « bon côté de la surface » : le segment entre
                    // l'ancrage (hauteur d'épaule du porteur) et la caméra résolue
                    // ne doit jamais recouper le collider du mur.
                    var cameraWorldPosition = anchor.transform.TransformPoint(localOffset);
                    Assert.That(
                        Physics.Linecast(anchor.transform.position, cameraWorldPosition, worldMask),
                        Is.False,
                        "Le segment ancrage->caméra ne doit jamais traverser le collider du mur.");
                }

                // Le mur laisse une face libre à 2,4 m le long d'un bras presque
                // aligné sur -Z : la caméra doit s'être arrêtée là, nettement en
                // deçà de sa longueur de repos, pas être restée à distance pleine.
                Assert.That(lastDistance, Is.LessThan(restDistance - 0.5f));
                Assert.That(
                    springArm.IsCloseOcclusionActive,
                    Is.False,
                    "À cette distance de contact le bras n'est pas assez court pour l'anti-occultation.");
            }
            finally
            {
                Object.DestroyImmediate(anchor);
                Object.DestroyImmediate(wall);
            }
        }

        [UnityTest]
        public IEnumerator Resolve_ClampsToTheMinimumDistanceWhenTheWallIsExtremelyClose()
        {
            var anchor = new GameObject("SpringArmAnchorClose");
            var wall = CreateWorldWall(
                "WallRightBehindPlayer",
                new Vector3(0f, 1.05f, -0.5f),
                new Vector3(5f, 5f, 0.4f));
            try
            {
                anchor.transform.position = new Vector3(0f, 1.05f, 0f);
                Physics.SyncTransforms();

                var springArm = new M1ThirdPersonSpringArm();
                var lastDistance = 0f;

                for (var frame = 0; frame < 10; frame++)
                {
                    yield return null;
                    lastDistance = springArm.Resolve(anchor.transform, RestLocalOffset, Time.deltaTime).magnitude;
                    Assert.That(
                        lastDistance,
                        Is.GreaterThanOrEqualTo(M1ThirdPersonSpringArm.MinimumDistanceMeters - 0.0005f),
                        "Un mur trop proche ne doit jamais faire descendre le bras sous le plancher.");
                }

                // Le contact moins la marge tomberait ici largement sous le
                // plancher : c'est le plancher qui doit gagner, pas le contact.
                Assert.That(
                    lastDistance,
                    Is.EqualTo(M1ThirdPersonSpringArm.MinimumDistanceMeters).Within(0.0005f));
                Assert.That(
                    springArm.IsCloseOcclusionActive,
                    Is.True,
                    "Le bras est au plus court : le corps du porteur doit basculer en ombre seule.");
            }
            finally
            {
                Object.DestroyImmediate(anchor);
                Object.DestroyImmediate(wall);
            }
        }

        [UnityTest]
        public IEnumerator Resolve_ExtendsGraduallyInsteadOfSnappingWhenTheWallDisappears()
        {
            var anchor = new GameObject("SpringArmAnchorExtend");
            var wall = CreateWorldWall("WallThatGoesAway", new Vector3(0f, 1.05f, -2.6f), new Vector3(5f, 5f, 0.4f));
            try
            {
                anchor.transform.position = new Vector3(0f, 1.05f, 0f);
                Physics.SyncTransforms();

                var springArm = new M1ThirdPersonSpringArm();
                var restDistance = RestLocalOffset.magnitude;
                var retractedDistance = 0f;

                // Laisse le bras se stabiliser contre le mur avant de le retirer.
                for (var frame = 0; frame < 15; frame++)
                {
                    yield return null;
                    retractedDistance = springArm.Resolve(anchor.transform, RestLocalOffset, Time.deltaTime)
                        .magnitude;
                }
                Assert.That(retractedDistance, Is.LessThan(restDistance - 0.5f));

                // Le mur disparaît : la sonde ne trouve plus rien devant elle, la
                // longueur cible remonte d'un coup à la valeur de repos.
                wall.SetActive(false);

                yield return null;
                var distanceOneFrameAfter = springArm
                    .Resolve(anchor.transform, RestLocalOffset, Time.deltaTime)
                    .magnitude;
                Assert.That(
                    distanceOneFrameAfter,
                    Is.GreaterThan(retractedDistance),
                    "La sortie doit commencer dès que le mur cesse d'occulter.");
                Assert.That(
                    distanceOneFrameAfter,
                    Is.LessThan(restDistance - 0.05f),
                    "Une caméra lissée n'est pas encore à sa place cible à la première frame.");

                // Assez de temps simulé (indépendant du framerate réel du test
                // runner) pour que le lissage exponentiel ait convergé.
                var elapsedSeconds = 0f;
                var settledDistance = distanceOneFrameAfter;
                while (elapsedSeconds < 2f)
                {
                    yield return null;
                    elapsedSeconds += Time.deltaTime;
                    settledDistance = springArm.Resolve(anchor.transform, RestLocalOffset, Time.deltaTime)
                        .magnitude;
                }

                Assert.That(settledDistance, Is.EqualTo(restDistance).Within(0.01f));
            }
            finally
            {
                Object.DestroyImmediate(anchor);
                Object.DestroyImmediate(wall);
            }
        }

        private static GameObject CreateWorldWall(string name, Vector3 position, Vector3 size)
        {
            var wall = GameObject.CreatePrimitive(PrimitiveType.Cube);
            wall.name = name;
            wall.layer = GameplayLayers.World;
            wall.transform.position = position;
            wall.transform.localScale = size;
            return wall;
        }
    }
}
