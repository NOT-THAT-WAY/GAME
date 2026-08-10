using FishNet.Object;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Bot d'entraînement du playtest labyrinthe : une cible qui marche et qu'on
    /// peut frapper. Spawné et piloté par l'hôte (NetworkTransform configuré
    /// server-authoritative), il avance en ligne droite et tourne quand un mur le bloque.
    /// Un coup validé par <see cref="PlayerPunch"/> l'étourdit ~1 s avec un knockback,
    /// puis il reprend sa marche.
    /// </summary>
    [RequireComponent(typeof(CharacterController))]
    public sealed class SimpleBot : NetworkBehaviour
    {
        private const float WalkSpeed = 2f;
        private const float TurnSpeed = 180f;
        private const float Gravity = -22f;

        // Portée du sondeur de mur : assez court pour longer un couloir sans
        // tourner en plein milieu, assez long pour amorcer le virage avant le nez
        // dans le mur.
        private const float WallProbeDistance = 0.9f;

        // Le sens alterne à chaque nouvel obstacle : toujours tourner du même côté
        // ferait boucler le bot sur le premier angle concave rencontré.
        private const float StaggerSeconds = 1f;
        private const float KnockbackDecay = 8f;

        // Inclinaison cosmétique du visuel pendant l'étourdissement.
        private const float StaggerTilt = 18f;

        [SerializeField] private Transform _visual;

        private CharacterController _controller;
        private Vector3 _knockback;
        private float _verticalVelocity;
        private float _staggeredUntil = float.NegativeInfinity;
        private float _turnDirection = 1f;
        private bool _turning;
        private bool _smokeHitLogged;

        private void Awake()
        {
            _controller = GetComponent<CharacterController>();
        }

        private void Update()
        {
            // Seul l'hôte déplace le bot ; les copies clientes suivent le
            // NetworkTransform.
            if (!IsServerStarted)
                return;

            if (Time.time < _staggeredUntil)
            {
                ApplyStaggered();
                return;
            }

            ApplyVisualTilt(0f);
            Walk();
        }

        /// <summary>
        /// Impulsion horizontale validée par l'hôte : le bot s'arrête un instant,
        /// recule et repart. Appelé côté serveur uniquement.
        /// </summary>
        public void ApplyKnockback(Vector3 velocity)
        {
            if (!IsServerStarted)
                return;

            velocity.y = 0f;
            _knockback = velocity;
            _staggeredUntil = Time.time + StaggerSeconds;
            if (!_smokeHitLogged)
            {
                _smokeHitLogged = true;
                HumanSmokeTestMode.LogEvent("bot_hit");
            }
        }

        /// <summary>
        /// Marche en ligne droite à hauteur de couloir. Un mur détecté devant
        /// lance une rotation sur place jusqu'à retrouver un passage libre.
        /// </summary>
        private void Walk()
        {
            if (WallAhead())
            {
                if (!_turning)
                {
                    _turning = true;
                    _turnDirection = -_turnDirection;
                }

                transform.Rotate(0f, TurnSpeed * _turnDirection * Time.deltaTime, 0f, Space.Self);
                return;
            }

            _turning = false;

            _verticalVelocity = _controller.isGrounded ? -3f : _verticalVelocity + Gravity * Time.deltaTime;

            var motion = transform.forward * WalkSpeed;
            motion.y = _verticalVelocity;
            _controller.Move(motion * Time.deltaTime);
        }

        /// <summary>Recul qui s'éteint tout seul, avec le tilt cosmétique.</summary>
        private void ApplyStaggered()
        {
            _verticalVelocity = _controller.isGrounded ? -3f : _verticalVelocity + Gravity * Time.deltaTime;

            var motion = _knockback;
            motion.y = _verticalVelocity;
            _controller.Move(motion * Time.deltaTime);
            _knockback = Vector3.MoveTowards(_knockback, Vector3.zero, KnockbackDecay * Time.deltaTime);

            var remaining = Mathf.InverseLerp(0f, StaggerSeconds, _staggeredUntil - Time.time);
            ApplyVisualTilt(StaggerTilt * remaining);
        }

        private void ApplyVisualTilt(float tilt)
        {
            if (_visual != null)
                _visual.localRotation = Quaternion.Euler(tilt, 0f, 0f);
        }

        /// <summary>
        /// Sonde à hauteur de poitrine : un tir au sol prendrait les gravats pour
        /// des murs, un tir aux yeux passerait au-dessus des gravats bloquants.
        /// </summary>
        private bool WallAhead()
        {
            var chest = transform.TransformPoint(_controller.center);
            return Physics.Raycast(chest, transform.forward, WallProbeDistance, ~0, QueryTriggerInteraction.Ignore);
        }
    }
}
