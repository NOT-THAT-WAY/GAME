using NotThatWay.Game.Sandbox;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Pose cosmétique du bras droit quand le lance-pierre ou un caillou est en
    /// main : une IK à deux os amène le poing au point de prise partagé avec l'objet
    /// (<see cref="SandboxPlayerGameplay.GetSlingshotGrip"/>), après l'Animator
    /// et sur tous les postes, en vue subjective comme à la troisième personne.
    /// Aucune règle n'en dépend : la capsule, la portée et le tir sont ailleurs.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(SandboxPlayerGameplay))]
    public sealed class M1SlingshotArmPose : MonoBehaviour
    {
        private const float BlendSeconds = 0.15f;
        // Le coude part vers l'extérieur et vers le bas, comme un bras qui tend
        // une fourche devant soi.
        private static readonly Vector3 ElbowHintLocal = new(0.55f, 0.55f, 0.10f);

        [SerializeField] private Transform _body;

        private SandboxPlayerGameplay _gameplay;
        private Transform _upperArm;
        private Transform _forearm;
        private Transform _hand;
        private Quaternion _upperArmRest;
        private Quaternion _forearmRest;
        private Quaternion _handRest;
        private float _upperLength;
        private float _foreLength;
        private float _weight;

        private void Awake()
        {
            _gameplay = GetComponent<SandboxPlayerGameplay>();
            var root = _body != null ? _body : transform;
            foreach (var child in root.GetComponentsInChildren<Transform>(true))
            {
                var name = child.name.ToLowerInvariant();
                if (!name.EndsWith(".r"))
                    continue;
                if (name.Contains("upperarm"))
                    _upperArm = child;
                else if (name.Contains("forearm"))
                    _forearm = child;
                else if (name.Contains("hand"))
                    _hand = child;
            }
            if (_upperArm == null || _forearm == null || _hand == null)
                return;
            _upperArmRest = _upperArm.localRotation;
            _forearmRest = _forearm.localRotation;
            _handRest = _hand.localRotation;
            _upperLength = Vector3.Distance(_upperArm.position, _forearm.position);
            _foreLength = Vector3.Distance(_forearm.position, _hand.position);
        }

        private void LateUpdate()
        {
            if (_upperArm == null || _forearm == null || _hand == null || _gameplay == null)
                return;

            var activeKind = _gameplay.ActiveKind;
            var raised = activeKind == SandboxCarryableKind.Slingshot ||
                         activeKind == SandboxCarryableKind.Rock;
            var target = raised ? 1f : 0f;
            _weight = Mathf.MoveTowards(_weight, target, Time.deltaTime / BlendSeconds);
            if (_weight <= 0f)
                return;

            // Sans clip qui anime le bras, l'Animator laisse les os où ils sont :
            // repartir de la pose de repos garantit un fondu propre à l'aller
            // comme au retour.
            _upperArm.localRotation = _upperArmRest;
            _forearm.localRotation = _forearmRest;
            _hand.localRotation = _handRest;
            var restUpper = _upperArm.rotation;
            var restFore = _forearm.rotation;

            _gameplay.GetSlingshotGrip(out var gripPosition, out _);
            SolveTwoBone(gripPosition);

            _upperArm.rotation = Quaternion.Slerp(restUpper, _upperArm.rotation, _weight);
            _forearm.rotation = Quaternion.Slerp(restFore, _forearm.rotation, _weight);
        }

        /// <summary>IK analytique : le coude se place sur le cercle des solutions, du côté de l'indice.</summary>
        private void SolveTwoBone(Vector3 target)
        {
            var shoulder = _upperArm.position;
            var reach = Mathf.Max(_upperLength + _foreLength - 0.001f, 0.001f);
            var toTarget = target - shoulder;
            var distance = Mathf.Clamp(toTarget.magnitude, 0.001f, reach);
            var direction = toTarget / Mathf.Max(toTarget.magnitude, 0.0001f);

            var frame = _gameplay.PresentationFrame;
            var hint = frame.TransformPoint(ElbowHintLocal) - shoulder;
            var side = hint - direction * Vector3.Dot(hint, direction);
            if (side.sqrMagnitude < 0.0001f)
                side = Vector3.Cross(direction, Vector3.up);
            side.Normalize();

            var along = (_upperLength * _upperLength - _foreLength * _foreLength + distance * distance) /
                        (2f * distance);
            var height = Mathf.Sqrt(Mathf.Max(_upperLength * _upperLength - along * along, 0f));
            var elbow = shoulder + direction * along + side * height;

            _upperArm.rotation = Quaternion.FromToRotation(_forearm.position - shoulder, elbow - shoulder) *
                                 _upperArm.rotation;
            _forearm.rotation = Quaternion.FromToRotation(_hand.position - _forearm.position, target - _forearm.position) *
                                _forearm.rotation;
        }
    }
}
