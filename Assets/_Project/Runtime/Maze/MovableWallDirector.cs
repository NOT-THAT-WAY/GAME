using System;
using System.Collections.Generic;
using FishNet.Object;
using FishNet.Object.Synchronizing;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Détient la pose de tous les murs mobiles de la map et la réplique.
    ///
    /// Un coup de poing fait pivoter un mur d'un quart de tour autour du bout
    /// opposé à l'impact : on pousse le battant, la charnière est en face. Le mur
    /// change donc d'axe et se pose sur l'arête perpendiculaire, exactement — un
    /// mur fait un pas de grille de long, et un quart de tour autour d'un nœud le
    /// mène d'une arête de la grille à une autre sans pose intermédiaire possible.
    ///
    /// Même contrat que <see cref="PivotDirector"/> : ce qui circule est un état
    /// discret par mur — son arête et son nombre de quarts de tour, empaquetés
    /// dans un entier — et jamais un transform image par image. Deux machines qui
    /// affichent des angles intermédiaires différents restent d'accord sur le
    /// labyrinthe, parce qu'elles convergent vers la même arête.
    ///
    /// L'hôte décide seul. Le client n'envoie même pas de cible : il envoie une
    /// intention de frappe à <see cref="PlayerPunch"/>, et c'est la copie serveur
    /// du décor qui désigne le mur touché, puis valide portée, repos, éloignement
    /// de l'arête d'origine, occupation de l'arête d'arrivée et absence de joueur
    /// dessous.
    ///
    /// Règle de collision retenue pour ce prototype : un mur ne se referme jamais
    /// sur quelqu'un. Si un joueur ou un bot occupe l'arête d'arrivée, la poussée
    /// est simplement refusée — pas de KO, pas de déplacement forcé. L'ADR 0004
    /// laisse cette conséquence ouverte ; c'est le choix explicite en attendant.
    /// </summary>
    public sealed class MovableWallDirector : NetworkBehaviour
    {
        /// <summary>Pas de grille du design : couloir 2,50 m plus mur 0,25 m.</summary>
        public const float GridPitch = 2.75f;

        // Une porte lourde : elle démarre mollement, prend son élan et se pose. Le
        // repos est juste au-dessus de la durée du battement, pour qu'on puisse
        // continuer à la pousser sans jamais reprendre un mur en plein vol.
        private const float SwingSeconds = 0.85f;
        private const float SwingCooldown = 0.95f;

        // Un mur ne s'éloigne jamais de plus de deux pas de son arête d'origine :
        // la map reste lisible et un mur ne traverse pas la moitié du plateau.
        private const float MaxDistanceFromHome = GridPitch * 2f + 0.01f;

        // Portée de validation serveur, mesurée depuis le segment du mur et non
        // depuis son centre : un mur fait un pas de grille de long. La marge couvre
        // le déplacement du frappeur pendant le trajet du message.
        private const float ServerReach = 3f;

        // Volume d'arrivée testé contre les joueurs : mur de 0,25 m et rayon de
        // capsule de 0,45 m, plus un peu de marge.
        private const float ClearanceHalfWidth = 0.8f;
        private const float ClearanceHalfLength = GridPitch * 0.5f + 0.45f;

        [SerializeField] private int _width = 16;
        [SerializeField] private int _height = 16;

        // Arêtes qu'aucun mur mobile ne peut occuper : le pourtour de la map, qui
        // doit rester fermé, et les bras de pivot, qui tournent sur place. Posées à
        // la génération depuis la grille, donc identiques sur les trois machines.
        [SerializeField] private int[] _blockedSlots = Array.Empty<int>();

        private readonly SyncList<int> _poses = new();
        private readonly HashSet<int> _occupied = new();

        private MovableWall[] _walls = Array.Empty<MovableWall>();
        private float[] _nextSwingAllowedAt = Array.Empty<float>();

        // Animation du battant, propre à chaque machine et jamais répliquée : elle
        // rattrape la pose reçue, elle ne la décide pas.
        private int[] _shownPose = Array.Empty<int>();
        private Vector3[] _swingHinge = Array.Empty<Vector3>();
        private Vector3[] _swingFromPosition = Array.Empty<Vector3>();
        private Quaternion[] _swingFromRotation = Array.Empty<Quaternion>();
        private float[] _swingAngle = Array.Empty<float>();
        private float[] _swingProgress = Array.Empty<float>();

        /// <summary>
        /// Les murs sont retrouvés dans la scène et triés par leur identifiant, posé
        /// à la génération. Aucune référence n'est sérialisée : le director est un
        /// prefab spawné par l'hôte, il ne peut pas pointer des objets de scène.
        /// </summary>
        private void ResolveWalls()
        {
            var walls = FindObjectsByType<MovableWall>(FindObjectsSortMode.None);
            Array.Sort(walls, (left, right) => left.Id.CompareTo(right.Id));
            _walls = walls;

            _shownPose = new int[walls.Length];
            for (var index = 0; index < walls.Length; index++)
                _shownPose[index] = -1;

            _swingHinge = new Vector3[walls.Length];
            _swingFromPosition = new Vector3[walls.Length];
            _swingFromRotation = new Quaternion[walls.Length];
            _swingAngle = new float[walls.Length];
            _swingProgress = new float[walls.Length];
        }

        public override void OnStartServer()
        {
            base.OnStartServer();

            ResolveWalls();
            _nextSwingAllowedAt = new float[_walls.Length];

            _occupied.Clear();
            foreach (var slot in _blockedSlots)
                _occupied.Add(slot);

            _poses.Clear();
            foreach (var wall in _walls)
            {
                var slot = SlotKey(wall.HomeFamily, wall.HomeSlotX, wall.HomeSlotY);
                _poses.Add(Pack(slot, 0));
                _occupied.Add(slot);
            }

            Debug.Log($"[GAME-MUR] {_walls.Length} mur(s) mobile(s) sous autorité de l'hôte, {_blockedSlots.Length} arête(s) interdite(s).");
        }

        public override void OnStartClient()
        {
            base.OnStartClient();

            // L'hôte a déjà résolu la liste en démarrant le serveur.
            if (_walls.Length == 0)
                ResolveWalls();

            Debug.Log($"[GAME-MUR] {_walls.Length} mur(s) mobile(s) dans la scène, état reçu pour {_poses.Count}.");
        }

        private void Update()
        {
            // Chaque machine rejoue la même cible : la pose affichée rattrape l'arête
            // répliquée, sans que personne n'envoie de transform. Une différence entre
            // pose reçue et pose affichée déclenche le battement local.
            var count = Mathf.Min(_walls.Length, _poses.Count);
            for (var index = 0; index < count; index++)
            {
                var wall = _walls[index];
                if (wall == null)
                    continue;

                var pose = _poses[index];
                if (_shownPose[index] != pose)
                    BeginSwing(index, pose);

                if (_swingProgress[index] >= 1f)
                    continue;

                _swingProgress[index] = Mathf.Min(1f, _swingProgress[index] + Time.deltaTime / SwingSeconds);

                var rotation = Quaternion.AngleAxis(_swingAngle[index] * Ease(_swingProgress[index]), Vector3.up);
                wall.transform.SetPositionAndRotation(
                    _swingHinge[index] + rotation * (_swingFromPosition[index] - _swingHinge[index]),
                    rotation * _swingFromRotation[index]);
            }
        }

        /// <summary>
        /// Prépare le battement vers une pose reçue. Sans pose précédente connue —
        /// premier affichage, ou arrivée en cours de partie — le mur se cale
        /// directement : on n'anime pas un mouvement qu'on n'a pas vu commencer.
        /// </summary>
        private void BeginSwing(int index, int pose)
        {
            var previous = _shownPose[index];
            _shownPose[index] = pose;

            if (previous < 0 || !TryFindHinge(SlotOf(previous), SlotOf(pose), out var hinge))
            {
                _walls[index].transform.SetPositionAndRotation(
                    SlotCenter(SlotOf(pose)), Quaternion.AngleAxis(90f * TurnsOf(pose), Vector3.up));
                _swingProgress[index] = 1f;
                return;
            }

            _swingHinge[index] = NodePosition(hinge);
            _swingFromPosition[index] = SlotCenter(SlotOf(previous));
            _swingFromRotation[index] = Quaternion.AngleAxis(90f * TurnsOf(previous), Vector3.up);
            _swingAngle[index] = Mathf.DeltaAngle(90f * TurnsOf(previous), 90f * TurnsOf(pose));
            _swingProgress[index] = 0f;
        }

        /// <summary>Départ et arrivée mous, plein élan au milieu : le poids d'un vantail de pierre.</summary>
        private static float Ease(float t)
        {
            return t * t * t * (t * (t * 6f - 15f) + 10f);
        }

        /// <summary>
        /// Fait pivoter un mur d'un quart de tour si l'hôte l'accepte. Appelé
        /// uniquement côté serveur, depuis la validation d'une frappe : le client n'a
        /// désigné ni le mur, ni le gond, ni le sens.
        /// </summary>
        /// <param name="wall">Mur touché sur la copie serveur du décor.</param>
        /// <param name="puncherPosition">Position répliquée du frappeur.</param>
        /// <param name="puncherForward">Regard du frappeur, qui donne le sens.</param>
        /// <param name="impactPoint">Point touché, qui désigne le battant donc le gond.</param>
        /// <returns>Vrai si l'arête du mur a changé.</returns>
        public bool TrySwing(MovableWall wall, Vector3 puncherPosition, Vector3 puncherForward, Vector3 impactPoint)
        {
            if (!IsServerStarted || wall == null)
                return false;

            var id = wall.Id;
            if (id < 0 || id >= _walls.Length || id >= _poses.Count || _walls[id] != wall)
                return false;

            if (Time.time < _nextSwingAllowedAt[id])
                return false;

            var pose = _poses[id];
            var slot = SlotOf(pose);
            var family = FamilyOf(slot);

            if (DistanceToWall(puncherPosition, SlotCenter(slot), SlotAxis(family)) > ServerReach)
                return false;

            EdgeNodes(family, XOf(slot), YOf(slot), out var nodeA, out var nodeB);
            var worldA = NodePosition(nodeA);
            var worldB = NodePosition(nodeB);

            // Le gond est le bout opposé à l'impact : on pousse le battant, jamais la
            // charnière. Frapper près d'un bout fait donc pivoter le mur autour de
            // l'autre, comme on ouvre une porte par sa poignée.
            var hingeIsA = (impactPoint - worldA).sqrMagnitude > (impactPoint - worldB).sqrMagnitude;
            var hinge = hingeIsA ? nodeA : nodeB;
            var leaf = hingeIsA ? nodeB : nodeA;
            var hingeWorld = hingeIsA ? worldA : worldB;
            var leafWorld = hingeIsA ? worldB : worldA;

            var arm = leaf - hinge;
            var forward = puncherForward;
            forward.y = 0f;
            forward.Normalize();

            var bestScore = float.NegativeInfinity;
            var bestSlot = -1;
            var bestTurn = 0;

            for (var sign = -1; sign <= 1; sign += 2)
            {
                // Quart de tour dans le repère de la grille, des deux côtés.
                var rotated = sign > 0
                    ? new Vector2Int(-arm.y, arm.x)
                    : new Vector2Int(arm.y, -arm.x);

                var targetLeaf = hinge + rotated;
                var targetSlot = SlotForEdge(hinge, targetLeaf);
                if (targetSlot < 0 || _occupied.Contains(targetSlot))
                    continue;

                // Le battant part du côté où l'on pousse.
                var targetLeafWorld = NodePosition(targetLeaf);
                var score = Vector3.Dot(forward, targetLeafWorld - leafWorld);
                if (score <= bestScore)
                    continue;

                bestScore = score;
                bestSlot = targetSlot;

                // Le sens de rotation se relit sur la géométrie et non sur le signe de
                // grille : les deux axes du plan sont retournés à l'export du FBX.
                bestTurn = Vector3.SignedAngle(leafWorld - hingeWorld, targetLeafWorld - hingeWorld, Vector3.up) > 0f
                    ? 1
                    : -1;
            }

            if (bestSlot < 0)
                return false;

            var home = SlotCenter(wall.HomeFamily, wall.HomeSlotX, wall.HomeSlotY, _width, _height);
            if (Vector3.Distance(SlotCenter(bestSlot), home) > MaxDistanceFromHome)
                return false;

            if (!IsClearOfPlayers(SlotCenter(bestSlot), SlotAxis(FamilyOf(bestSlot))))
                return false;

            _occupied.Remove(slot);
            _occupied.Add(bestSlot);
            _poses[id] = Pack(bestSlot, TurnsOf(pose) + bestTurn);
            _nextSwingAllowedAt[id] = Time.time + SwingCooldown;
            return true;
        }

        /// <summary>
        /// Nœud commun à deux arêtes, donc gond du quart de tour qui mène de l'une à
        /// l'autre. Faux si les deux arêtes ne se touchent pas, ce qui ne devrait
        /// arriver que sur un état incohérent.
        /// </summary>
        private static bool TryFindHinge(int fromSlot, int toSlot, out Vector2Int hinge)
        {
            EdgeNodes(FamilyOf(fromSlot), XOf(fromSlot), YOf(fromSlot), out var fromA, out var fromB);
            EdgeNodes(FamilyOf(toSlot), XOf(toSlot), YOf(toSlot), out var toA, out var toB);

            if (fromA == toA || fromA == toB)
            {
                hinge = fromA;
                return true;
            }

            if (fromB == toA || fromB == toB)
            {
                hinge = fromB;
                return true;
            }

            hinge = Vector2Int.zero;
            return false;
        }

        /// <summary>
        /// Les deux nœuds que relie une arête. Une arête verticale monte d'un cran en
        /// y, une horizontale avance d'un cran en x.
        /// </summary>
        private static void EdgeNodes(int family, int x, int y, out Vector2Int first, out Vector2Int second)
        {
            first = new Vector2Int(x, y);
            second = family == 0 ? new Vector2Int(x, y + 1) : new Vector2Int(x + 1, y);
        }

        /// <summary>Arête reliant deux nœuds voisins, ou -1 si elle sort de la grille.</summary>
        private int SlotForEdge(Vector2Int first, Vector2Int second)
        {
            int family, x, y;
            if (first.x == second.x)
            {
                family = 0;
                x = first.x;
                y = Mathf.Min(first.y, second.y);
            }
            else
            {
                family = 1;
                x = Mathf.Min(first.x, second.x);
                y = first.y;
            }

            var maxX = family == 0 ? _width : _width - 1;
            var maxY = family == 0 ? _height - 1 : _height;
            if (x < 0 || x > maxX || y < 0 || y > maxY)
                return -1;

            return SlotKey(family, x, y);
        }

        /// <summary>
        /// Distance horizontale au segment du mur. Mesurer depuis son centre
        /// refuserait une frappe légitime portée près d'un bout, le mur faisant un
        /// pas de grille entier de long.
        /// </summary>
        private static float DistanceToWall(Vector3 point, Vector3 center, Vector3 axis)
        {
            var offset = point - center;
            offset.y = 0f;

            var along = Mathf.Clamp(Vector3.Dot(offset, axis), -GridPitch * 0.5f, GridPitch * 0.5f);
            return (offset - axis * along).magnitude;
        }

        /// <summary>
        /// Vrai si personne n'occupe l'arête d'arrivée. Les positions répliquées
        /// suffisent : le mur ne se referme sur personne, il ne part simplement pas.
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

        /// <summary>Direction unitaire d'une arête. Les deux axes du plan sont retournés à l'export.</summary>
        private static Vector3 SlotAxis(int family)
        {
            return family == 0 ? Vector3.back : Vector3.left;
        }

        private Vector3 NodePosition(Vector2Int node)
        {
            return new Vector3(
                -(node.x - _width / 2f) * GridPitch,
                0f,
                -(node.y - _height / 2f) * GridPitch);
        }

        private Vector3 SlotCenter(int slot)
        {
            return SlotCenter(FamilyOf(slot), XOf(slot), YOf(slot), _width, _height);
        }

        /// <summary>
        /// Centre monde d'une arête de la grille. Même convention d'axes que les
        /// centres de cellule du générateur de scène : l'export FBX retourne les deux
        /// axes du plan, d'où les signes.
        /// </summary>
        public static Vector3 SlotCenter(int family, int x, int y, int width, int height)
        {
            var nodeX = x - width / 2f;
            var nodeY = y - height / 2f;
            if (family == 0)
                nodeY += 0.5f;
            else
                nodeX += 0.5f;

            return new Vector3(-nodeX * GridPitch, 0f, -nodeY * GridPitch);
        }

        /// <summary>
        /// Clé d'une arête. Les index de grille tiennent largement dans les tranches
        /// réservées : la map fait 16x16, la borne est à mille.
        /// </summary>
        public static int SlotKey(int family, int x, int y)
        {
            return family * 1_000_000 + x * 1_000 + y;
        }

        // Pose répliquée : l'arête et le nombre de quarts de tour dans un seul
        // entier. Les quarts de tour ne servent qu'à poser la bonne face du maillage
        // sculpté ; l'arête, elle, décide de la collision.
        private static int Pack(int slot, int turns) => slot * 4 + (turns & 3);

        private static int SlotOf(int pose) => pose / 4;

        private static int TurnsOf(int pose) => pose & 3;

        private static int FamilyOf(int slot) => slot / 1_000_000;

        private static int XOf(int slot) => slot % 1_000_000 / 1_000;

        private static int YOf(int slot) => slot % 1_000;
    }
}
