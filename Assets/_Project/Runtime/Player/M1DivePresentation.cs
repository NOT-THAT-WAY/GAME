using NotThatWay.Game.PlayerSimulation;
using NotThatWay.Game.Sandbox;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Posture cosmétique du plongeon et du ramper : le corps bascule vers l'avant
    /// en vol, s'étale au sol (atterrissage ou plat ventre) et se redresse au
    /// relevé ; la caméra descend à hauteur d'yeux de la posture, sans jamais
    /// tourner. Tout vient de l'état simulé (ADR 0004) ; l'interpolation locale en
    /// <see cref="Time.deltaTime"/> ne décide d'aucune règle. La cible est le
    /// corps importé seul, jamais un parent de la caméra.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(PredictedPlayerMotor))]
    public sealed class M1DivePresentation : MonoBehaviour
    {
        private const float AirborneTiltDegrees = 78f;
        private const float ProneTiltDegrees = 90f;
        private const float TiltLerpPerSecond = 14f;
        private const float CrawlEyeHeightMeters = 0.55f;

        [SerializeField] private Transform _body;
        [SerializeField] private Transform _cameraPivot;

        private PredictedPlayerMotor _motor;
        private SandboxPlayerGameplay _gameplay;
        private Quaternion _baseRotation = Quaternion.identity;
        private Vector3 _basePosition;
        private Vector3 _cameraRestPosition;
        private float _tilt;
        private uint _recoveryTotalTicks;

        // Géométrie du modèle, mesurée une fois : hauteur du point le plus bas au
        // repos (les pieds) et portée avant maximale. Voir ProneLiftMeters.
        private float _restLowestMeters;
        private float _forwardReachMeters;

        private void Awake()
        {
            _motor = GetComponent<PredictedPlayerMotor>();
            _gameplay = GetComponent<SandboxPlayerGameplay>();
            if (_body != null)
            {
                _baseRotation = _body.localRotation;
                _basePosition = _body.localPosition;
                MeasureBody();
            }
            if (_cameraPivot != null)
                _cameraRestPosition = _cameraPivot.localPosition;
        }

        private void Update()
        {
            if (_body == null || _motor == null || !_motor.IsSimulationReady)
                return;

            var state = _motor.SimulationState;
            float target;
            if (_gameplay != null && !_gameplay.IsAlive)
            {
                // KO : au sol, à plat, jusqu'au relevé volontaire.
                target = ProneTiltDegrees;
                _recoveryTotalTicks = 0u;
            }
            else if (state.IsDiving)
            {
                target = AirborneTiltDegrees;
                _recoveryTotalTicks = 0u;
            }
            else if (state.IsCrawling)
            {
                target = ProneTiltDegrees;
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
            _body.localPosition = _basePosition + Vector3.up * ProneLiftMeters(
                _tilt,
                _restLowestMeters,
                _forwardReachMeters);

            // Les yeux suivent la posture : à plat ventre, la caméra descend —
            // translation verticale seulement, jamais de rotation.
            if (_cameraPivot != null)
            {
                var eye = Mathf.Lerp(
                    _cameraRestPosition.y,
                    CrawlEyeHeightMeters,
                    flatness);
                _cameraPivot.localPosition = new Vector3(
                    _cameraRestPosition.x,
                    eye,
                    _cameraRestPosition.z);
            }
        }

        /// <summary>
        /// Le pivot de bascule est aux pieds : après une rotation de θ autour de
        /// X, un point (y, z) du modèle arrive à <c>y·cos θ − z·sin θ</c>. Le
        /// point le plus bas devient donc <c>ymin·cos θ − zmax·sin θ</c> — à plat
        /// ventre (θ = 90°), toute la moitié avant du corps passe SOUS le sol.
        /// On remonte exactement de ce que la bascule a fait descendre : debout
        /// (θ = 0) le décalage est nul et la pose de repos ne bouge pas, à plat
        /// le corps repose sur le sol au lieu d'y être enfoncé.
        ///
        /// Strictement cosmétique. La forme physique du joueur reste la capsule
        /// du <c>CharacterController</c>, dont la hauteur ne vient que de l'état
        /// simulé du tick (ADR 0004) et que ce composant ne touche jamais.
        /// </summary>
        public static float ProneLiftMeters(
            float tiltDegrees,
            float restLowestMeters,
            float forwardReachMeters)
        {
            var tilt = tiltDegrees * Mathf.Deg2Rad;
            var lowest = restLowestMeters * Mathf.Cos(tilt) -
                         forwardReachMeters * Mathf.Sin(tilt);
            return restLowestMeters - lowest;
        }

        /// <summary>
        /// Mesure le modèle au lieu de coder sa silhouette en dur : un export
        /// plus grand ou plus rond corrige la posture tout seul. Les bornes
        /// viennent des maillages, dans le repère du corps — pas d'une boîte
        /// englobante monde, qui dépendrait du lacet du joueur à l'instant du
        /// réveil.
        /// </summary>
        private void MeasureBody()
        {
            var lowest = float.PositiveInfinity;
            var forward = float.NegativeInfinity;
            var toBody = _body.worldToLocalMatrix;
            foreach (var renderer in _body.GetComponentsInChildren<Renderer>(true))
            {
                var mesh = renderer is SkinnedMeshRenderer skinned
                    ? skinned.sharedMesh
                    : renderer.TryGetComponent<MeshFilter>(out var filter)
                        ? filter.sharedMesh
                        : null;
                if (mesh == null)
                    continue;

                var matrix = toBody * renderer.transform.localToWorldMatrix;
                var bounds = mesh.bounds;
                for (var corner = 0; corner < 8; corner++)
                {
                    var sign = new Vector3(
                        (corner & 1) == 0 ? -1f : 1f,
                        (corner & 2) == 0 ? -1f : 1f,
                        (corner & 4) == 0 ? -1f : 1f);
                    var point = _baseRotation * matrix.MultiplyPoint3x4(
                        bounds.center + Vector3.Scale(bounds.extents, sign));
                    lowest = Mathf.Min(lowest, point.y);
                    forward = Mathf.Max(forward, point.z);
                }
            }

            if (float.IsInfinity(lowest) || float.IsInfinity(forward))
            {
                // Aucun maillage mesurable : ne rien inventer, la posture garde
                // simplement sa pose de repos.
                _restLowestMeters = 0f;
                _forwardReachMeters = 0f;
                return;
            }

            _restLowestMeters = lowest;
            _forwardReachMeters = Mathf.Max(0f, forward);
            // Une ligne par objet joueur : un export au gabarit différent doit se
            // lire dans le journal de banc, pas se découvrir à l'écran.
            Debug.Log(
                $"[GAME-POSTURE] body_measured restLowest={_restLowestMeters:F3} " +
                $"forwardReach={_forwardReachMeters:F3} " +
                $"proneLift={ProneLiftMeters(ProneTiltDegrees, _restLowestMeters, _forwardReachMeters):F3}.",
                this);
        }
    }
}
