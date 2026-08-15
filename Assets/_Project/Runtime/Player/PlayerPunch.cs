using FishNet.Object;
using NotThatWay.Game.Input;
using NotThatWay.Game.PlayerSimulation;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Coup de poing prototype du playtest labyrinthe. Le clic gauche joue l'animation
    /// en local pour la réactivité, puis demande la validation à l'hôte : cooldown
    /// et recherche de cible sont mesurés côté serveur. Un coup qui ne trouve
    /// personne cherche un mur mobile devant le poing et demande à
    /// <see cref="MovableWallDirector"/> de l'ébranler. Le mouvement reste
    /// client-authoritative (dette du smoke test) : l'hôte ne téléporte personne,
    /// le knockback d'un joueur est appliqué par son propre client via
    /// <see cref="PlayerMotor.ApplyKnockbackFromServer"/>. Le combat final relève de M1,
    /// après la migration décrite par l'ADR 0004.
    /// </summary>
    [RequireComponent(typeof(PlayerMotor))]
    [RequireComponent(typeof(PlayerInputSource))]
    public sealed class PlayerPunch : NetworkBehaviour
    {
        // Le clip fait 20 images à 24 i/s (~0,83 s) : le cooldown couvre l'action
        // sans laisser marteler F plus vite que le bras ne revient.
        private const float PunchCooldown = 0.8f;

        // Le bras part droit devant : un coup n'attrape que ce qui est dans le
        // prolongement du regard, à bout de bras. Le couloir fait 2,50 m.
        private const float PunchRange = 2f;
        private const float PunchHalfAngle = 30f;

        // Impulsion horizontale qui décroît dans PlayerMotor : assez fort pour
        // décoller la victime de son appui, pas pour la traverser d'un mur.
        private const float KnockbackSpeed = 4.5f;

        // Marge de validation côté serveur : la victime a bougé depuis l'appui du
        // frappeur, et la latence ne doit pas annuler un coup légitime.
        private const float ServerRangeTolerance = 1f;

        private static readonly int PunchTrigger = Animator.StringToHash("Punch");

        // Hauteur du poing, réutilisée pour la ligne de vue et pour le rayon qui
        // cherche un mur : un coup part de la poitrine, pas des pieds.
        private const float ChestHeight = 0.7f;

        private PlayerMotor _motor;
        private PlayerInputSource _inputSource;
        private Animator _animator;
        private MovableWallDirector _wallDirector;
        // Le host possède la même instance côté client et côté serveur. Deux
        // horloges séparées évitent que le filtre local refuse immédiatement sa
        // propre requête serveur.
        private float _nextLocalPunchAllowedAt = float.NegativeInfinity;
        private float _nextServerPunchAllowedAt = float.NegativeInfinity;
        private bool _smokePunchLogged;

        private void Awake()
        {
            _motor = GetComponent<PlayerMotor>();
            _inputSource = GetComponent<PlayerInputSource>();
            _animator = GetComponentInChildren<Animator>(true);
        }

        private void Update()
        {
            if (!IsOwner)
                return;

            var pressed = _inputSource != null
                ? _inputSource.CurrentFrame.PressedButtons
                : PlayerCommandButtons.None;
            if ((pressed & PlayerCommandButtons.PunchPressed) == 0)
                return;

            // Filtre local sur le même tempo que le serveur : inutile de faire
            // voyager un appui que l'hôte refuserait.
            if (Time.time < _nextLocalPunchAllowedAt)
                return;

            _nextLocalPunchAllowedAt = Time.time + PunchCooldown;
            PlayPunch();
            RequestPunchServerRpc();
        }

        /// <summary>Joue l'animation du coup, si le visuel riggé est présent.</summary>
        private void PlayPunch()
        {
            if (_animator != null)
                _animator.SetTrigger(PunchTrigger);
        }

        /// <summary>
        /// Intention de frapper envoyée à l'hôte. C'est lui qui mesure le cooldown,
        /// cherche une victime dans le cône devant le frappeur et distribue les
        /// effets : animation chez tous, knockback chez la victime.
        /// </summary>
        [ServerRpc]
        private void RequestPunchServerRpc()
        {
            if (Time.time < _nextServerPunchAllowedAt)
                return;

            _nextServerPunchAllowedAt = Time.time + PunchCooldown;

            var victimPlayer = (PlayerMotor)null;
            var victimBot = (SimpleBot)null;
            FindVictim(out victimPlayer, out victimBot);

            if (!_smokePunchLogged)
            {
                _smokePunchLogged = true;
                var target = victimPlayer != null ? "player" : victimBot != null ? "bot" : "environment_or_empty";
                HumanSmokeTestMode.LogEvent("punch", $"target={target}");
            }

            PlayPunchObserversRpc();

            var direction = transform.forward;
            direction.y = 0f;
            direction.Normalize();

            if (victimPlayer != null)
                victimPlayer.ApplyKnockbackFromServer(direction * KnockbackSpeed);
            else if (victimBot != null)
                victimBot.ApplyKnockback(direction * KnockbackSpeed);
            else
                TryPunchWall();
        }

        /// <summary>
        /// Coup porté dans le vide : si un mur mobile est à portée devant le poing,
        /// l'hôte l'ébranle. Un coup ne suffit pas à l'ouvrir — il verse sa part
        /// d'effort et il en faut trois enchaînés. La cible, le gond et le sens sont
        /// résolus là-bas, sur la copie serveur du décor — le client n'a désigné
        /// aucun mur et ne peut donc pas en pousser un qu'il ne voit pas.
        /// </summary>
        private void TryPunchWall()
        {
            if (_wallDirector == null)
                _wallDirector = FindFirstObjectByType<MovableWallDirector>();

            if (_wallDirector == null)
                return;

            var origin = transform.position + Vector3.up * ChestHeight;
            if (!Physics.Raycast(origin, transform.forward, out var hit, PunchRange, ~0, QueryTriggerInteraction.Ignore))
                return;

            var wall = hit.collider.GetComponentInParent<MovableWall>();
            if (wall == null)
                return;

            HumanSmokeTestMode.LogEventOnce(
                "wall_punch_contact_local",
                "wall_punch_contact",
                $"id={wall.Id} distance={hit.distance:F2}");
            _wallDirector.TryPunch(wall, transform.position, transform.forward, hit.point);
        }

        /// <summary>
        /// Cible la plus proche dans le cône de frappe, parmi les autres joueurs et
        /// les bots. La position répliquée décide portée et cône ; un Linecast
        /// serveur court empêche ensuite de toucher au travers d'un mur.
        /// </summary>
        private void FindVictim(out PlayerMotor victimPlayer, out SimpleBot victimBot)
        {
            victimPlayer = null;
            victimBot = null;

            var origin = transform.position;
            var bestDistance = float.PositiveInfinity;

            foreach (var player in FindObjectsByType<PlayerMotor>(FindObjectsSortMode.None))
            {
                if (player == _motor)
                    continue;

                var distance = DistanceInCone(origin, player.transform.position);
                if (distance >= bestDistance || !HasLineOfSight(player.transform))
                    continue;

                bestDistance = distance;
                victimPlayer = player;
                victimBot = null;
            }

            foreach (var bot in FindObjectsByType<SimpleBot>(FindObjectsSortMode.None))
            {
                var distance = DistanceInCone(origin, bot.transform.position);
                if (distance >= bestDistance || !HasLineOfSight(bot.transform))
                    continue;

                bestDistance = distance;
                victimPlayer = null;
                victimBot = bot;
            }
        }

        /// <summary>
        /// Distance horizontale de la cible si elle est dans le cône de frappe,
        /// l'infini sinon. La tolérance compense le déplacement de la victime
        /// pendant le trajet du message.
        /// </summary>
        private float DistanceInCone(Vector3 origin, Vector3 target)
        {
            var offset = target - origin;
            offset.y = 0f;

            var distance = offset.magnitude;
            if (distance > PunchRange + ServerRangeTolerance)
                return float.PositiveInfinity;

            if (distance > 0.01f && Vector3.Angle(transform.forward, offset) > PunchHalfAngle)
                return float.PositiveInfinity;

            return distance;
        }

        /// <summary>
        /// Empêche de frapper au travers d'un mur. Une cible distante peut ne pas
        /// avoir de CharacterController actif sur la copie serveur ; l'absence de
        /// hit signifie donc « passage libre », tandis qu'un hit appartenant à la
        /// cible est accepté.
        /// </summary>
        private bool HasLineOfSight(Transform target)
        {
            var start = transform.position + Vector3.up * ChestHeight;
            var end = target.position + Vector3.up * ChestHeight;

            if (!Physics.Linecast(start, end, out var hit, ~0, QueryTriggerInteraction.Ignore))
                return true;

            return hit.transform == target || hit.transform.IsChildOf(target);
        }

        /// <summary>L'animation du frappeur chez tous ; le propriétaire l'a déjà jouée.</summary>
        [ObserversRpc(ExcludeOwner = true)]
        private void PlayPunchObserversRpc()
        {
            PlayPunch();
        }
    }
}
