using UnityEngine;

namespace NotThatWay.Game.Sandbox
{
    /// <summary>
    /// Contrat entre le gameplay déjà fonctionnel et les futurs clips Blender.
    /// Aucun événement d'animation ne décide d'un hit : ce pont ne fait que
    /// présenter l'état calculé par la simulation et l'autorité serveur.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(PredictedPlayerMotor))]
    [RequireComponent(typeof(SandboxPlayerGameplay))]
    public sealed class SandboxPlayerAnimationBridge : MonoBehaviour
    {
        private static readonly int MoveSpeedFloat = Animator.StringToHash("MoveSpeed");
        private static readonly int GroundedBool = Animator.StringToHash("Grounded");
        private static readonly int SprintingBool = Animator.StringToHash("Sprinting");
        private static readonly int JumpTrigger = Animator.StringToHash("Jump");
        private static readonly int LandTrigger = Animator.StringToHash("Land");
        private static readonly int CarryingBool = Animator.StringToHash("Carrying");
        private static readonly int CarryKindInt = Animator.StringToHash("CarryKind");
        private static readonly int KnockedOutBool = Animator.StringToHash("KnockedOut");
        private static readonly int DiveTrigger = Animator.StringToHash("Dive");
        private static readonly int DivingBool = Animator.StringToHash("Diving");
        private static readonly int DiveRecoveringBool = Animator.StringToHash("DiveRecovering");

        // La marche M1 plafonne à 4,2 m/s ; le sprint avec trophée atteint
        // 5,25 m/s. Un seuil à 4,3 sépare donc les deux profils sans connaître
        // les entrées locales d'un proxy distant.
        private const float SprintPresentationThreshold = 4.3f;

        private PredictedPlayerMotor _motor;
        private SandboxPlayerGameplay _gameplay;
        private Animator _animator;
        private bool _hasGroundedSample;
        private bool _wasGrounded;
        private bool _wasDiving;

        private void Awake()
        {
            _motor = GetComponent<PredictedPlayerMotor>();
            _gameplay = GetComponent<SandboxPlayerGameplay>();
            _animator = GetComponentInChildren<Animator>(true);
        }

        private void Update()
        {
            if (_animator == null || _animator.runtimeAnimatorController == null ||
                _motor == null || !_motor.IsSimulationReady)
            {
                return;
            }

            var state = _motor.SimulationState;
            var speed = (float)state.HorizontalVelocity.HorizontalMagnitude;
            var alive = _gameplay == null || _gameplay.IsAlive;
            var activeKind = _gameplay?.ActiveKind ?? SandboxCarryableKind.None;
            _animator.SetFloat(MoveSpeedFloat, speed);
            _animator.SetBool(GroundedBool, state.IsGrounded);
            _animator.SetBool(
                SprintingBool,
                alive && !state.IsDiving && speed > SprintPresentationThreshold);
            _animator.SetBool(DivingBool, state.IsDiving);
            _animator.SetBool(DiveRecoveringBool, state.DiveRecoveryTicksRemaining > 0u);
            if (state.IsDiving && !_wasDiving)
                _animator.SetTrigger(DiveTrigger);
            _wasDiving = state.IsDiving;
            _animator.SetBool(CarryingBool, activeKind != SandboxCarryableKind.None);
            _animator.SetInteger(CarryKindInt, (int)activeKind);
            _animator.SetBool(KnockedOutBool, !alive);

            if (_hasGroundedSample)
            {
                // Le décollage d'un plongeon a son propre déclencheur : ne pas le
                // doubler d'un saut.
                if (_wasGrounded && !state.IsGrounded && state.VerticalVelocity > 0d &&
                    !state.IsDiving)
                {
                    _animator.SetTrigger(JumpTrigger);
                }
                else if (!_wasGrounded && state.IsGrounded)
                    _animator.SetTrigger(LandTrigger);
            }
            _wasGrounded = state.IsGrounded;
            _hasGroundedSample = true;
        }
    }
}
