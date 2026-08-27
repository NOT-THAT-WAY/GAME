using NotThatWay.Game.PlayerSimulation;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Posture cosmétique du plongeon : le corps bascule vers l'avant pendant le
    /// vol, s'étale au sol à l'arrivée puis se redresse sur la durée du relevé.
    /// Tout vient de l'état simulé (ADR 0004) ; l'interpolation locale en
    /// <see cref="Time.deltaTime"/> ne décide d'aucune règle. La cible est le
    /// corps importé seul, jamais un parent de la caméra : la vue reste droite.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(PredictedPlayerMotor))]
    public sealed class M1DivePresentation : MonoBehaviour
    {
        private const float AirborneTiltDegrees = 78f;
        private const float ProneTiltDegrees = 90f;
        private const float TiltLerpPerSecond = 14f;
        // Le pivot de bascule est aux pieds : à plat, le bassin descend vers le sol
        // pour que le corps ne flotte pas à hauteur de hanches.
        private const float ProneDropMeters = 0.12f;

        [SerializeField] private Transform _body;

        private PredictedPlayerMotor _motor;
        private Quaternion _baseRotation = Quaternion.identity;
        private Vector3 _basePosition;
        private float _tilt;
        private uint _recoveryTotalTicks;

        private void Awake()
        {
            _motor = GetComponent<PredictedPlayerMotor>();
            if (_body != null)
            {
                _baseRotation = _body.localRotation;
                _basePosition = _body.localPosition;
            }
        }

        private void Update()
        {
            if (_body == null || _motor == null || !_motor.IsSimulationReady)
                return;

            var state = _motor.SimulationState;
            float target;
            if (state.IsDiving)
            {
                target = AirborneTiltDegrees;
                _recoveryTotalTicks = 0u;
            }
            else if (state.DiveRecoveryTicksRemaining > 0u)
            {
                // Le premier échantillon du relevé fixe sa durée totale : la
                // config n'est pas connue ici et ce n'est qu'une présentation.
                if (_recoveryTotalTicks < state.DiveRecoveryTicksRemaining)
                    _recoveryTotalTicks = state.DiveRecoveryTicksRemaining;
                target = ProneTiltDegrees * state.DiveRecoveryTicksRemaining / _recoveryTotalTicks;
            }
            else
            {
                target = 0f;
                _recoveryTotalTicks = 0u;
            }

            _tilt = Mathf.Lerp(_tilt, target, 1f - Mathf.Exp(-TiltLerpPerSecond * Time.deltaTime));
            var flatness = Mathf.InverseLerp(AirborneTiltDegrees, ProneTiltDegrees, _tilt);
            _body.localRotation = Quaternion.Euler(_tilt, 0f, 0f) * _baseRotation;
            _body.localPosition = _basePosition + Vector3.down * (ProneDropMeters * flatness);
        }
    }
}
