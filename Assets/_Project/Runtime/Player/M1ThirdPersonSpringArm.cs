using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Bras à ressort de la caméra troisième personne du banc M1. Purement
    /// cosmétique et local (ADR 0004) : aucun état partagé, aucun tick, aucune
    /// règle réseau n'en dépend, ce qui permet de le tester sans FishNet — voir
    /// <c>M1ThirdPersonSpringArmPlayModeTests</c>. La logique est volontairement
    /// séparée de <see cref="M1PlayerAppearance"/>, qui reste le seul appelant
    /// autorisé côté porteur local.
    /// </summary>
    public sealed class M1ThirdPersonSpringArm
    {
        /// <summary>
        /// Rayon de la sonde. Un simple rayon ne verrait pas un mur d'angle par
        /// un interstice ; une sphère de la largeur approximative d'une tête le
        /// détecte avant que le plan proche de la caméra n'atteigne la surface.
        /// </summary>
        public const float SphereCastRadiusMeters = 0.25f;

        /// <summary>
        /// Marge gardée devant le point de contact, pour ne jamais coller le
        /// plan proche de la caméra sur la surface (scintillement / clip).
        /// </summary>
        public const float ContactMarginMeters = 0.2f;

        /// <summary>
        /// Distance plancher : en dessous, le personnage se retrouverait caché
        /// derrière son propre modèle et la caméra risquerait d'entrer dans son
        /// volume. Tenue même si un mur est plus proche que ça — voir
        /// <see cref="M1PlayerAppearance"/> pour l'anti-occultation qui masque
        /// alors le corps plutôt que de laisser un clip franc.
        /// </summary>
        public const float MinimumDistanceMeters = 1.2f;

        /// <summary>
        /// Sous ce seuil, le bras est considéré « très court » : le corps du
        /// porteur bascule en ombre seule pour ne pas boucher l'écran. Une bande
        /// au-dessus du plancher plutôt que le plancher lui-même, pour ne pas
        /// osciller au pixel près quand la distance résolue frôle le minimum.
        /// </summary>
        public const float CloseOcclusionThresholdMeters = 1.5f;

        /// <summary>
        /// Vitesse de la remontée exponentielle, en /s, indépendante du
        /// framerate : à 10, le bras a comblé ~63 % de l'écart restant après
        /// 100 ms et ~95 % après 300 ms, à 30 comme à 120 FPS.
        /// </summary>
        public const float ExtendSharpnessPerSecond = 10f;

        /// <summary>
        /// Zoom maximal demandé par le testeur : la caméra peut se rapprocher
        /// jusqu'à 25 % de moins que sa distance de repos, jamais plus.
        /// </summary>
        public const float MinimumZoomFactor = 0.75f;

        /// <summary>Distance de repos pleine, sans aucun zoom appliqué.</summary>
        public const float MaximumZoomFactor = 1f;

        private float _currentDistanceMeters = -1f;
        private float _zoomFactor = MaximumZoomFactor;

        /// <summary>
        /// Vrai quand le bras est resté sous <see cref="CloseOcclusionThresholdMeters"/>
        /// après le dernier <see cref="Resolve"/>.
        /// </summary>
        public bool IsCloseOcclusionActive { get; private set; }

        /// <summary>
        /// Facteur courant appliqué à la longueur de repos du bras, toujours
        /// dans [<see cref="MinimumZoomFactor"/>, <see cref="MaximumZoomFactor"/>].
        /// Exposé pour les tests et pour un futur indicateur de zoom à l'écran.
        /// </summary>
        public float ZoomFactor => _zoomFactor;

        /// <summary>
        /// Applique l'entrée de zoom de la frame (molette ou croix manette,
        /// déjà convertie en delta de facteur par <c>PlayerInputSource</c>).
        /// <see cref="Mathf.Clamp"/> absorbe en un seul appel toute rafale
        /// démesurée (trackpad) : le facteur ne peut jamais sortir de
        /// [<see cref="MinimumZoomFactor"/>, <see cref="MaximumZoomFactor"/>],
        /// quelle que soit l'amplitude de <paramref name="zoomFactorDelta"/>.
        /// Ne touche jamais <see cref="_currentDistanceMeters"/> : c'est
        /// <see cref="Resolve"/> qui recombine zoom et anti-mur à la prochaine
        /// frame. Survit volontairement à <see cref="Reset"/> — la bascule
        /// 1re/3e personne ne doit pas remettre le zoom à zéro.
        /// </summary>
        public void ApplyZoomInput(float zoomFactorDelta)
        {
            _zoomFactor = Mathf.Clamp(_zoomFactor + zoomFactorDelta, MinimumZoomFactor, MaximumZoomFactor);
        }

        /// <summary>
        /// Calcule la position locale (relative à <paramref name="anchor"/>) de
        /// la caméra pour cette frame : sonde vers <paramref name="restLocalOffset"/>
        /// contre le seul layer <see cref="GameplayLayers.World"/>, ramène le
        /// bras au contact moins une marge s'il touche, et lisse la seule
        /// longueur du bras — rentrée immédiate, sortie progressive.
        /// </summary>
        public Vector3 Resolve(Transform anchor, Vector3 restLocalOffset, float deltaTime)
        {
            if (anchor == null)
            {
                Reset();
                return restLocalOffset * _zoomFactor;
            }

            var restDistance = restLocalOffset.magnitude;
            if (restDistance <= Mathf.Epsilon)
            {
                _currentDistanceMeters = 0f;
                IsCloseOcclusionActive = false;
                return Vector3.zero;
            }

            var localDirection = restLocalOffset / restDistance;
            var worldDirection = anchor.TransformDirection(localDirection);

            // Le zoom n'est qu'un plafond sur la longueur de repos, jamais un
            // nouvel offset : la sonde anti-mur travaille toujours en dessous de
            // ce plafond, jamais au-dessus, donc un mur raccourcit toujours plus
            // que ne le ferait le zoom seul. Max avec la distance plancher :
            // même si _zoomFactor descendait un jour sous ce qu'il faut pour
            // rester au-dessus du plancher, le zoom ne doit jamais pouvoir
            // l'enfoncer.
            var zoomedRestDistance = Mathf.Max(MinimumDistanceMeters, restDistance * _zoomFactor);

            var targetDistance = zoomedRestDistance;
            if (Physics.SphereCast(
                    anchor.position,
                    SphereCastRadiusMeters,
                    worldDirection,
                    out var hit,
                    zoomedRestDistance,
                    1 << GameplayLayers.World,
                    QueryTriggerInteraction.Ignore))
            {
                targetDistance = Mathf.Max(MinimumDistanceMeters, hit.distance - ContactMarginMeters);
            }

            if (_currentDistanceMeters < 0f || targetDistance < _currentDistanceMeters)
            {
                // Rentrée immédiate (et premier calcul) : le moindre retard
                // laisserait voir l'intérieur du mur pendant une frame.
                _currentDistanceMeters = targetDistance;
            }
            else
            {
                var smoothing = 1f - Mathf.Exp(-ExtendSharpnessPerSecond * deltaTime);
                _currentDistanceMeters = Mathf.Lerp(_currentDistanceMeters, targetDistance, smoothing);
            }

            IsCloseOcclusionActive = _currentDistanceMeters <= CloseOcclusionThresholdMeters;
            return localDirection * _currentDistanceMeters;
        }

        /// <summary>
        /// Oublie la longueur courante. À appeler en entrant en vue troisième
        /// personne, pour que le bras reparte d'un calcul frais au lieu
        /// d'hériter d'une distance retenue d'une session précédente.
        /// </summary>
        public void Reset()
        {
            _currentDistanceMeters = -1f;
            IsCloseOcclusionActive = false;
        }
    }
}
