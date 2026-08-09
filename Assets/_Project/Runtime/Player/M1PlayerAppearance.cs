using FishNet.Connection;
using FishNet.Object;
using UnityEngine;
using UnityEngine.Rendering;

namespace NotThatWay.Game
{
    /// <summary>
    /// Habillage du personnage M1 : teinte stable par propriétaire et corps
    /// masqué pour son propre porteur en vue première personne. Purement
    /// cosmétique, exécuté à l'arrivée du client, sans état partagé ni tick.
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

        [SerializeField] private Transform _body;

        private Renderer[] _renderers;

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
            // Les références sont prises avant que FishNet ne détache l'objet
            // graphique de la racine ; elles restent valides après le reparentage.
            var root = _body != null ? _body : transform;
            _renderers = root.GetComponentsInChildren<Renderer>(true);
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
            if (_renderers == null)
                return;

            var color = ColorForOwner();
            var properties = new MaterialPropertyBlock();
            foreach (var renderer in _renderers)
            {
                if (renderer == null)
                    continue;

                renderer.GetPropertyBlock(properties);
                properties.SetColor(BaseColorId, color);
                properties.SetColor(LegacyColorId, color);
                renderer.SetPropertyBlock(properties);

                // Le porteur voit par les yeux du personnage : afficher son propre
                // maillage ne montrerait que l'intérieur de sa tête. L'ombre reste
                // rendue, ce qui garde un repère au sol sans occulter la vue.
                renderer.shadowCastingMode = IsOwner
                    ? ShadowCastingMode.ShadowsOnly
                    : ShadowCastingMode.On;
            }
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
