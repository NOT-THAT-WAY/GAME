using System;
using NotThatWay.Game.PlayerSimulation;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Frontière PLY-01 vers Unity. Le CharacterController est déplacé exactement
    /// une fois par appel et sa pose résolue redevient la vérité du modèle pur.
    /// </summary>
    public sealed class UnityCharacterControllerWorld : IPlayerCollisionWorld
    {
        private const float PoseMismatchToleranceSquared = 0.00000001f;

        private readonly CharacterController _controller;

        public UnityCharacterControllerWorld(CharacterController controller)
        {
            _controller = controller != null
                ? controller
                : throw new ArgumentNullException(nameof(controller));
        }

        public CharacterController Controller => _controller;

        public PlayerCollisionResult Move(in PlayerCollisionRequest request)
        {
            if (!_controller.enabled)
                throw new InvalidOperationException("CharacterController désactivé pendant un tick simulé.");

            // La capsule est celle que la requête décrit : ramper l'abaisse, les
            // pieds restant au sol (centre = hauteur/2, convention du prefab).
            var height = (float)request.PlayerHeightMeters;
            if (Mathf.Abs(_controller.height - height) > 0.0001f)
            {
                _controller.height = height;
                _controller.center = new Vector3(0f, height * 0.5f, 0f);
            }

            var expectedStart = ToUnity(request.StartPosition, nameof(request.StartPosition));
            if ((_controller.transform.position - expectedStart).sqrMagnitude >
                PoseMismatchToleranceSquared)
            {
                SetPose(request.StartPosition, request.YawCentidegrees);
            }
            else
            {
                _controller.transform.rotation = Quaternion.Euler(
                    0f,
                    request.YawCentidegrees / 100f,
                    0f);
            }

            var unityFlags = _controller.Move(ToUnity(
                request.DesiredDisplacement,
                nameof(request.DesiredDisplacement)));
            var flags = PlayerCollisionFlags.None;
            if ((unityFlags & CollisionFlags.Sides) != 0)
                flags |= PlayerCollisionFlags.Sides;
            if ((unityFlags & CollisionFlags.Above) != 0)
                flags |= PlayerCollisionFlags.Above;
            if ((unityFlags & CollisionFlags.Below) != 0)
                flags |= PlayerCollisionFlags.Below;

            return new PlayerCollisionResult(ToDomain(_controller.transform.position), flags);
        }

        public void SetPose(PlayerVector3 position, int yawCentidegrees)
        {
            if (yawCentidegrees < 0 || yawCentidegrees >= PlayerState.FullYawCentidegrees)
                throw new ArgumentOutOfRangeException(nameof(yawCentidegrees));

            var wasEnabled = _controller.enabled;
            if (wasEnabled)
                _controller.enabled = false;
            _controller.transform.SetPositionAndRotation(
                ToUnity(position, nameof(position)),
                Quaternion.Euler(0f, yawCentidegrees / 100f, 0f));
            if (wasEnabled)
                _controller.enabled = true;
        }

        public static PlayerVector3 ToDomain(Vector3 value) =>
            new(value.x, value.y, value.z);

        private static Vector3 ToUnity(PlayerVector3 value, string parameterName) => new(
            ToFiniteFloat(value.X, parameterName),
            ToFiniteFloat(value.Y, parameterName),
            ToFiniteFloat(value.Z, parameterName));

        private static float ToFiniteFloat(double value, string parameterName)
        {
            if (double.IsNaN(value) || double.IsInfinity(value) ||
                value < -float.MaxValue || value > float.MaxValue)
            {
                throw new ArgumentOutOfRangeException(parameterName);
            }

            return (float)value;
        }
    }
}
