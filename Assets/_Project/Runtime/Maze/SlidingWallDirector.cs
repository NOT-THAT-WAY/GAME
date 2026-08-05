using System;
using System.Collections.Generic;
using FishNet.Object;
using FishNet.Object.Synchronizing;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Détient la position de tous les murs coulissants de la map et la réplique.
    ///
    /// Même contrat que <see cref="PivotDirector"/> : ce qui circule est un état
    /// discret par mur — un décalage entier en cases de grille — et jamais un
    /// transform image par image. Deux machines qui affichent des positions
    /// intermédiaires différentes restent d'accord sur le labyrinthe, parce
    /// qu'elles convergent vers la même case.
    ///
    /// L'hôte décide seul. Le client n'envoie même pas de cible : il envoie une
    /// intention de frappe à <see cref="PlayerPunch"/>, et c'est la copie serveur
    /// du décor qui désigne le mur touché, puis valide portée, borne de
    /// déplacement, occupation de la case d'arrivée et absence de joueur dessous.
    ///
    /// Règle de collision retenue pour ce prototype : un mur ne se referme jamais
    /// sur quelqu'un. Si un joueur ou un bot occupe la case d'arrivée, la poussée
    /// est simplement refusée — pas de KO, pas de déplacement forcé. L'ADR 0004
    /// laisse cette conséquence ouverte ; c'est le choix explicite en attendant.
    /// </summary>
    public sealed class SlidingWallDirector : NetworkBehaviour
    {
        /// <summary>Pas de grille du design : couloir 2,50 m plus mur 0,25 m.</summary>
        public const float GridPitch = 2.75f;

        // Un mur ne s'éloigne jamais de plus de deux cases de son origine : la map
        // reste lisible et un mur ne peut pas traverser la moitié du plateau.
        private const int MaxOffset = 2;

        // Durée d'un glissement d'une case et repos entre deux poussées du même
        // mur. Purement cosmétique pour la première, le temps que la case
        // répliquée soit atteinte ; la seconde est mesurée par l'hôte.
        private const float SlideSeconds = 0.5f;
        private const float SlideCooldown = 0.6f;

        // Portée de validation serveur, mesurée depuis le segment du mur et non
        // depuis son centre : un mur fait une case de long. La marge couvre le
        // déplacement du frappeur pendant le trajet du message.
        private const float ServerReach = 3f;

        // Demi-largeur du volume d'arrivée testé contre les joueurs : mur de
        // 0,25 m et rayon de capsule de 0,45 m, plus un peu de marge.
        private const float ClearanceHalfWidth = 0.8f;
        private const float ClearanceHalfLength = GridPitch * 0.5f + 0.45f;

        [SerializeField] private int _width = 16;
        [SerializeField] private int _height = 16;

        // Cases d'arête tenues par un bras de pivot : elles ne bougent pas et
        // aucun mur coulissant ne peut s'y garer. Posées à la génération depuis
        // l'état 2 de la grille, donc identiques sur les trois machines.
        [SerializeField] private int[] _blockedSlots = Array.Empty<int>();

        private readonly SyncList<int> _offsets = new();
        private readonly HashSet<int> _occupied = new();
        private SlidingWall[] _walls = Array.Empty<SlidingWall>();
        private float[] _nextSlideAllowedAt = Array.Empty<float>();

        /// <summary>
        /// Les murs sont retrouvés dans la scène et triés par leur identifiant,
        /// posé à la génération. Aucune référence n'est sérialisée : le director
        /// est un prefab spawné par l'hôte, il ne peut pas pointer des objets de
        /// scène.
        /// </summary>
        private void ResolveWalls()
        {
            var walls = FindObjectsByType<SlidingWall>(FindObjectsSortMode.None);
            Array.Sort(walls, (left, right) => left.Id.CompareTo(right.Id));
            _walls = walls;
        }

        public override void OnStartServer()
        {
            base.OnStartServer();

            ResolveWalls();
            _nextSlideAllowedAt = new float[_walls.Length];

            _occupied.Clear();
            foreach (var slot in _blockedSlots)
                _occupied.Add(slot);

            _offsets.Clear();
            foreach (var wall in _walls)
            {
                _offsets.Add(0);
                _occupied.Add(SlotKey(wall.Family, wall.SlotX, wall.SlotY));
            }

            Debug.Log($"[GAME-MUR] {_walls.Length} mur(s) coulissant(s) sous autorité de l'hôte, {_blockedSlots.Length} case(s) tenue(s) par un pivot.");
        }

        public override void OnStartClient()
        {
            base.OnStartClient();

            // L'hôte a déjà résolu la liste en démarrant le serveur.
            if (_walls.Length == 0)
                ResolveWalls();

            Debug.Log($"[GAME-MUR] {_walls.Length} mur(s) coulissant(s) dans la scène, état reçu pour {_offsets.Count}.");
        }

        private void Update()
        {
            // Chaque machine rejoue la même cible : la position affichée rattrape
            // la case répliquée, sans que personne n'envoie de position.
            var count = Mathf.Min(_walls.Length, _offsets.Count);
            var step = GridPitch / SlideSeconds * Time.deltaTime;

            for (var index = 0; index < count; index++)
            {
                var wall = _walls[index];
                if (wall == null)
                    continue;

                var target = wall.PositionForOffset(_offsets[index]);
                var current = wall.transform.position;
                if (current != target)
                    wall.transform.position = Vector3.MoveTowards(current, target, step);
            }
        }

        /// <summary>
        /// Fait glisser un mur d'une case si l'hôte l'accepte. Appelé uniquement
        /// côté serveur, depuis la validation d'une frappe : le client n'a désigné
        /// ni le mur ni le sens.
        /// </summary>
        /// <param name="wall">Mur touché sur la copie serveur du décor.</param>
        /// <param name="puncherPosition">Position répliquée du frappeur.</param>
        /// <param name="puncherForward">Regard du frappeur, qui donne le sens.</param>
        /// <param name="impactPoint">Point touché, utilisé pour une frappe de plein fouet.</param>
        /// <returns>Vrai si la case du mur a changé.</returns>
        public bool TrySlide(SlidingWall wall, Vector3 puncherPosition, Vector3 puncherForward, Vector3 impactPoint)
        {
            if (!IsServerStarted || wall == null)
                return false;

            var id = wall.Id;
            if (id < 0 || id >= _walls.Length || id >= _offsets.Count || _walls[id] != wall)
                return false;

            if (Time.time < _nextSlideAllowedAt[id])
                return false;

            var axis = wall.Step.normalized;
            if (axis == Vector3.zero)
                return false;

            if (DistanceToWall(puncherPosition, wall.transform.position, axis) > ServerReach)
                return false;

            var direction = ResolveDirection(wall, axis, puncherForward, impactPoint);
            var offset = _offsets[id];
            var newOffset = offset + direction;
            if (Mathf.Abs(newOffset) > MaxOffset)
                return false;

            // Un mur ne change que l'index qui court sur les cellules : le vertical
            // glisse en y, l'horizontal en x. L'autre index tient le nœud et ne
            // bouge jamais, sinon le mur quitterait sa ligne.
            var vertical = wall.Family == 0;
            var currentX = vertical ? wall.SlotX : wall.SlotX + offset;
            var currentY = vertical ? wall.SlotY + offset : wall.SlotY;
            var targetX = vertical ? wall.SlotX : wall.SlotX + newOffset;
            var targetY = vertical ? wall.SlotY + newOffset : wall.SlotY;

            var limit = vertical ? _height : _width;
            var running = vertical ? targetY : targetX;
            if (running < 0 || running >= limit)
                return false;

            var targetSlot = SlotKey(wall.Family, targetX, targetY);
            if (_occupied.Contains(targetSlot))
                return false;

            if (!IsClearOfPlayers(wall.PositionForOffset(newOffset), axis))
                return false;

            _occupied.Remove(SlotKey(wall.Family, currentX, currentY));
            _occupied.Add(targetSlot);
            _offsets[id] = newOffset;
            _nextSlideAllowedAt[id] = Time.time + SlideCooldown;
            return true;
        }

        /// <summary>
        /// Sens du glissement. Le cas lisible est celui d'un joueur qui frappe le
        /// mur par son bout, dans le couloir qui le prolonge : le mur part devant
        /// lui. De plein fouet, le regard ne dit plus rien de l'axe du mur, et
        /// c'est le bord touché qui décide, comme une porte coulissante poussée
        /// par son montant.
        /// </summary>
        private static int ResolveDirection(SlidingWall wall, Vector3 axis, Vector3 puncherForward, Vector3 impactPoint)
        {
            var forward = puncherForward;
            forward.y = 0f;
            forward.Normalize();

            var facing = Vector3.Dot(forward, axis);
            if (Mathf.Abs(facing) > 0.25f)
                return facing > 0f ? 1 : -1;

            var along = Vector3.Dot(impactPoint - wall.transform.position, axis);
            return along > 0f ? -1 : 1;
        }

        /// <summary>
        /// Distance horizontale au segment du mur. Mesurer depuis son centre
        /// refuserait une frappe légitime portée près d'un bout, le mur faisant
        /// une case entière de long.
        /// </summary>
        private static float DistanceToWall(Vector3 point, Vector3 center, Vector3 axis)
        {
            var offset = point - center;
            offset.y = 0f;

            var along = Mathf.Clamp(Vector3.Dot(offset, axis), -GridPitch * 0.5f, GridPitch * 0.5f);
            return (offset - axis * along).magnitude;
        }

        /// <summary>
        /// Vrai si personne n'occupe la case d'arrivée. Les positions répliquées
        /// suffisent : le mur ne se referme sur personne, il ne part simplement
        /// pas.
        /// </summary>
        private static bool IsClearOfPlayers(Vector3 target, Vector3 axis)
        {
            foreach (var player in FindObjectsByType<PlayerMotor>(FindObjectsSortMode.None))
            {
                if (Overlaps(player.transform.position, target, axis))
                    return false;
            }

            foreach (var bot in FindObjectsByType<SimpleBot>(FindObjectsSortMode.None))
            {
                if (Overlaps(bot.transform.position, target, axis))
                    return false;
            }

            return true;
        }

        private static bool Overlaps(Vector3 position, Vector3 target, Vector3 axis)
        {
            var offset = position - target;
            offset.y = 0f;

            var along = Vector3.Dot(offset, axis);
            var across = (offset - axis * along).magnitude;
            return Mathf.Abs(along) < ClearanceHalfLength && across < ClearanceHalfWidth;
        }

        /// <summary>
        /// Clé d'une case d'arête. Les index de grille tiennent largement dans les
        /// tranches réservées : la map fait 16x16, la borne est à mille.
        /// </summary>
        public static int SlotKey(int family, int x, int y)
        {
            return family * 1_000_000 + x * 1_000 + y;
        }
    }
}
