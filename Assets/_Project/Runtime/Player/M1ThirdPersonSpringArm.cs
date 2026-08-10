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

        private float _currentDistanceMeters = -1f;

        /// <summary>
        /// Vrai quand le bras est resté sous <see cref="CloseOcclusionThresholdMeters"/>
        /// après le dernier <see cref="Resolve"/>.
        /// </summary>
        public bool IsCloseOcclusionActive { get; private set; }

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
                return restLocalOffset;
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

            var targetDistance = restDistance;
            if (Physics.SphereCast(
                    anchor.position,
                    SphereCastRadiusMeters,
                    worldDirection,
                    out var hit,
                    restDistance,
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
