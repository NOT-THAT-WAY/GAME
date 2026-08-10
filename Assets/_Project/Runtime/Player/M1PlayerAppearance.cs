using System;
using FishNet.Connection;
using FishNet.Object;
using NotThatWay.Game.Input;
using UnityEngine;
using UnityEngine.Rendering;

namespace NotThatWay.Game
{
    /// <summary>
    /// Habillage du personnage M1 : teinte stable par propriétaire, avant-bras
    /// visibles en vue subjective et bascule première/troisième personne. Tout
    /// est local et cosmétique — aucun état partagé, aucun tick, aucune règle.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class M1PlayerAppearance : NetworkBehaviour
    {
        private static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");
        private static readonly int LegacyColorId = Shader.PropertyToID("_Color");

        /// <summary>
        /// Teintes de banc, lisibles entre elles et distinctes du cyan du mur
        /// mobile comme des deux pads d'apparition.
        /// </summary>
        private static readonly Color[] OwnerColors =
        {
            new(0.94f, 0.83f, 0.42f),
            new(0.53f, 0.60f, 0.95f),
            new(0.87f, 0.52f, 0.80f),
            new(0.55f, 0.88f, 0.72f)
        };

        /// <summary>
        /// Parties que son porteur voit en vue subjective. Sans elles, pousser ou
        /// frapper ne produit aucun retour à l'écran : la caméra est à hauteur des
        /// yeux, donc à l'intérieur du volume du corps. Ces noms viennent de
        /// l'export et ne servent qu'au rendu — aucune règle gameplay ni aucun
        /// identifiant réseau n'en dépend (ADR 0004).
        /// </summary>
        private static readonly string[] FirstPersonVisibleParts = { "Forearm", "Fist" };

        private static readonly Vector3 FirstPersonCameraOffset = Vector3.zero;
        private static readonly Vector3 ThirdPersonCameraOffset = new(0f, 0.55f, -3.4f);

        [SerializeField] private Transform _body;
        [SerializeField] private Camera _camera;

        private PlayerInputSource _inputSource;
        private Renderer[] _renderers = Array.Empty<Renderer>();
        private bool[] _visibleInFirstPerson = Array.Empty<bool>();
        private bool _thirdPerson;

        /// <summary>
        /// Même table pour le jeu et pour les captures de contrôle du build.
        /// </summary>
        public static Color ColorForIndex(int index)
        {
            if (index < 0)
                index = -index;
            return OwnerColors[index % OwnerColors.Length];
        }

        private void Awake()
        {
            _inputSource = GetComponent<PlayerInputSource>();

            // Les références sont prises avant que FishNet ne détache l'objet
            // graphique de la racine ; elles restent valides après le reparentage.
            var root = _body != null ? _body : transform;
            _renderers = root.GetComponentsInChildren<Renderer>(true);
            _visibleInFirstPerson = new bool[_renderers.Length];
            for (var index = 0; index < _renderers.Length; index++)
                _visibleInFirstPerson[index] = IsFirstPersonPart(_renderers[index]);
        }

        private void Update()
        {
            if (!IsOwner || _inputSource == null || !_inputSource.ViewTogglePressedThisFrame)
                return;
            _thirdPerson = !_thirdPerson;
            ApplyAppearance();
        }

        public override void OnStartClient()
        {
            base.OnStartClient();
            ApplyAppearance();
        }

        public override void OnOwnershipClient(NetworkConnection previousOwner)
        {
            base.OnOwnershipClient(previousOwner);
            ApplyAppearance();
        }

        private void ApplyAppearance()
        {
            if (_camera != null && IsOwner)
            {
                _camera.transform.localPosition = _thirdPerson
                    ? ThirdPersonCameraOffset
                    : FirstPersonCameraOffset;
            }

            var color = ColorForOwner();
            var properties = new MaterialPropertyBlock();
            for (var index = 0; index < _renderers.Length; index++)
            {
                var renderer = _renderers[index];
                if (renderer == null)
                    continue;

                renderer.GetPropertyBlock(properties);
                properties.SetColor(BaseColorId, color);
                properties.SetColor(LegacyColorId, color);
                renderer.SetPropertyBlock(properties);

                // Le corps du porteur masquerait l'écran en vue subjective : il ne
                // garde que son ombre, tandis que ses avant-bras restent affichés.
                var visible = !IsOwner || _thirdPerson || _visibleInFirstPerson[index];
                renderer.shadowCastingMode = visible
                    ? ShadowCastingMode.On
                    : ShadowCastingMode.ShadowsOnly;
            }
        }

        /// <summary>
        /// Exposé pour que les captures de contrôle montrent exactement ce que
        /// voit le porteur, et non un corps entier qu'il n'aura jamais à l'écran.
        /// </summary>
        public static bool IsFirstPersonPart(Renderer value)
        {
            if (value == null)
                return false;
            foreach (var part in FirstPersonVisibleParts)
            {
                if (value.name.IndexOf(part, StringComparison.OrdinalIgnoreCase) >= 0)
                    return true;
            }

            return false;
        }

        /// <summary>
        /// L'identifiant de connexion est partagé par le serveur, donc toutes les
        /// fenêtres attribuent la même teinte au même joueur. Sans propriétaire
        /// connu, l'identifiant d'objet reste un repli stable.
        /// </summary>
        private Color ColorForOwner() =>
            ColorForIndex(Owner != null && Owner.IsValid ? Owner.ClientId : ObjectId);
    }
}
