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

        [Test]
        public void ApplyZoomInput_ClampsToBothExtremesEvenWithADisproportionateSingleInput()
        {
            var springArm = new M1ThirdPersonSpringArm();

            // Une seule rafale, bien plus grande que tout l'écart [75 %, 100 %] :
            // le genre de valeur qu'un trackpad peut envoyer d'un coup. Clamp
            // doit absorber ça en un seul appel, jamais de dépassement
            // transitoire ni de besoin d'appels supplémentaires pour rattraper.
            // Le delta s'ajoute au facteur de bras : négatif raccourcit donc
            // rapproche. C'est PlayerInputSource qui inverse la molette pour que
            // « vers l'avant » rapproche.
            springArm.ApplyZoomInput(-1000f);
            Assert.That(
                springArm.ZoomFactor,
                Is.EqualTo(M1ThirdPersonSpringArm.MinimumZoomFactor).Within(0.0005f),
                "Une rafale de zoom avant démesurée doit s'arrêter pile à la borne basse.");

            springArm.ApplyZoomInput(1000f);
            Assert.That(
                springArm.ZoomFactor,
                Is.EqualTo(M1ThirdPersonSpringArm.MaximumZoomFactor).Within(0.0005f),
                "Une rafale de zoom arrière démesurée doit s'arrêter pile à la borne haute.");
        }

        [UnityTest]
        public IEnumerator Resolve_AtMaximumZoomSettlesToSeventyFivePercentOfTheRestDistanceWithNoWallInTheWay()
        {
            var anchor = new GameObject("SpringArmAnchorZoomNoWall");
            try
            {
                anchor.transform.position = new Vector3(0f, 1.05f, 0f);
                Physics.SyncTransforms();

                var springArm = new M1ThirdPersonSpringArm();
                springArm.ApplyZoomInput(-1f);
                Assert.That(
                    springArm.ZoomFactor,
                    Is.EqualTo(M1ThirdPersonSpringArm.MinimumZoomFactor).Within(0.0005f));

                // Champ vide : rien ne clampe en dessous du plafond de zoom, donc
                // la distance résolue doit converger exactement sur 75 % de la
                // longueur réelle du bras. C'est ≈3,444 m, pas exactement les
                // 3,4 m de la seule composante Z citée dans la demande : l'offset
                // a aussi 0,55 m de hauteur, mise à l'échelle avec le reste
                // comme le fait déjà le raccourcissement anti-mur (zoom et
                // anti-mur reconstruisent tous deux la même direction unitaire
                // fois une distance).
                var restDistance = RestLocalOffset.magnitude;
                var expectedDistance = restDistance * M1ThirdPersonSpringArm.MinimumZoomFactor;
                var lastDistance = 0f;

                for (var frame = 0; frame < 10; frame++)
                {
                    yield return null;
                    lastDistance = springArm.Resolve(anchor.transform, RestLocalOffset, Time.deltaTime).magnitude;

                    Assert.That(
                        lastDistance,
                        Is.LessThanOrEqualTo(expectedDistance + 0.0005f),
                        "Le zoom est un plafond : la caméra ne doit jamais aller au-delà.");
                    Assert.That(
                        lastDistance,
                        Is.GreaterThanOrEqualTo(M1ThirdPersonSpringArm.MinimumDistanceMeters - 0.0005f));
                }

                Assert.That(lastDistance, Is.EqualTo(expectedDistance).Within(0.01f));
            }
            finally
            {
                Object.DestroyImmediate(anchor);
            }
        }

        [UnityTest]
        public IEnumerator Resolve_WallClampStaysTheSameRegardlessOfHowMuchTheUserHasZoomed()
        {
            // Mur nettement plus proche que même le plafond de zoom maximal
            // (75 % de ≈3,444 m ≈ 2,583 m) : si le zoom court-circuitait
            // l'anti-mur, le résultat différerait entre zoom normal et zoom
            // maximal. Il ne doit pas différer — c'est le mur qui décide,
            // jamais le zoom, quel que soit le facteur en cours.
            var wallPosition = new Vector3(0f, 1.05f, -1.8f);
            var wallSize = new Vector3(5f, 5f, 0.4f);
            var zoomCeiling = RestLocalOffset.magnitude * M1ThirdPersonSpringArm.MinimumZoomFactor;

            var anchorNormal = new GameObject("SpringArmAnchorWallNormalZoom");
            var wallNormal = CreateWorldWall("WallCloserThanZoomCeilingNormal", wallPosition, wallSize);
            var distanceAtNormalZoom = 0f;
            try
            {
                anchorNormal.transform.position = new Vector3(0f, 1.05f, 0f);
                Physics.SyncTransforms();

                var springArm = new M1ThirdPersonSpringArm();
                for (var frame = 0; frame < 10; frame++)
                {
                    yield return null;
                    distanceAtNormalZoom = springArm
                        .Resolve(anchorNormal.transform, RestLocalOffset, Time.deltaTime)
                        .magnitude;
                }
            }
            finally
            {
                Object.DestroyImmediate(anchorNormal);
                Object.DestroyImmediate(wallNormal);
            }

            var anchorZoomed = new GameObject("SpringArmAnchorWallMaximumZoom");
            var wallZoomed = CreateWorldWall("WallCloserThanZoomCeilingZoomed", wallPosition, wallSize);
            var distanceAtMaximumZoom = 0f;
            try
            {
                anchorZoomed.transform.position = new Vector3(0f, 1.05f, 0f);
                Physics.SyncTransforms();

                var springArm = new M1ThirdPersonSpringArm();
                springArm.ApplyZoomInput(-1f);
                Assert.That(
                    springArm.ZoomFactor,
                    Is.EqualTo(M1ThirdPersonSpringArm.MinimumZoomFactor).Within(0.0005f));

                for (var frame = 0; frame < 10; frame++)
                {
                    yield return null;
                    distanceAtMaximumZoom = springArm
                        .Resolve(anchorZoomed.transform, RestLocalOffset, Time.deltaTime)
                        .magnitude;
                }
            }
            finally
            {
                Object.DestroyImmediate(anchorZoomed);
                Object.DestroyImmediate(wallZoomed);
            }

            Assert.That(
                distanceAtNormalZoom,
                Is.LessThan(zoomCeiling - 0.3f),
                "Le mur doit être franchement en dessous du plafond de zoom pour que ce test prouve quelque chose.");
            Assert.That(
                distanceAtMaximumZoom,
                Is.EqualTo(distanceAtNormalZoom).Within(0.005f),
                "Le zoom ne doit jamais court-circuiter l'anti-mur : même mur, même distance de contact.");
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
