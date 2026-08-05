using System;
using System.Collections.Generic;
using FishNet.Connection;
using FishNet.Object;
using FishNet.Object.Synchronizing;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Détient la pose de tous les murs mobiles de la map et la réplique.
    ///
    /// Deux façons de bouger un mur, un seul effort. Marcher contre lui l'accumule
    /// lentement, comme un vantail de pierre qu'on épaule ; un coup de poing en
    /// verse un tiers d'un coup, et le mur reste ébranlé un instant avant de
    /// retomber — trois coups enchaînés le font donc basculer, un seul jamais.
    /// Dans les deux cas le mur pivote autour du bout opposé au contact : on
    /// pousse le battant, la charnière est en face. Le mur
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
    /// L'hôte décide seul. Le client n'envoie même pas de cible quand il frappe :
    /// la copie serveur du décor désigne le mur touché. Quand il pousse, il ne
    /// désigne que le mur, jamais le gond, le sens ni la durée de son effort —
    /// l'hôte mesure l'effort à son propre rythme, donc répéter l'intention plus
    /// vite ne fait pas céder le mur plus tôt. Dans les deux cas il valide portée,
    /// repos, ancrage à l'arête d'origine, occupation de l'arête d'arrivée et
    /// absence de joueur dessous.
    ///
    /// Un mur garde toujours un pied chez lui : son arête d'arrivée doit toucher
    /// un des deux nœuds de son arête d'origine. Sans cette borne, des coups
    /// répétés le font marcher d'arête en arête et il finit hors de vue derrière
    /// le labyrinthe — un mur qui « disparaît ».
    ///
    /// Une réserve à connaître : l'effort d'une poussée en cours est répliqué, par
    /// paliers de 5 %, pour que tout le monde voie le battant céder. C'est un
    /// scalaire par mur poussé et non un transform, mais c'est un cran de plus que
    /// l'état purement discret des pivots. La migration de l'ADR 0004 le remplace
    /// par une transition à `startTick`/`durationTicks`.
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

        // Poussée à l'épaule : lourde, mais pas au point qu'on renonce. L'effort
        // retombe un peu plus vite qu'il ne monte, donc lâcher ramène le battant.
        private const float PushSeconds = 3f;
        private const float ReleaseSeconds = 1.6f;

        // Un coup de poing verse un tiers de la course : trois coups ouvrent le
        // mur, un seul ne l'ouvre jamais. Le battant reste ébranlé plus longtemps
        // que le repos du poing, donc enchaîner les coups accumule vraiment ;
        // s'arrêter le laisse retomber.
        private const float PunchEffort = 0.34f;
        private const float PunchHoldSeconds = 1.4f;

        // Au-delà de ce silence, l'hôte considère que le joueur a cessé de pousser.
        // Le client répète son intention plus souvent que ça.
        private const float IntentTimeout = 0.25f;

        // Contact à l'épaule : plus court que la portée du poing, on doit toucher
        // le mur. La marge couvre le trajet du message.
        private const float PushReach = 1.8f;

        // L'effort répliqué est quantifié : inutile d'envoyer chaque centième. Vingt
        // paliers sur toute la course, lissés localement, suffisent à voir le mur
        // céder sans transformer un état partagé en flux de transform.
        private const int PushStep = 5;
        private const float PushSmoothing = 12f;

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

        // Poussée en cours par mur : arête visée et effort en pourcents, empaquetés.
        // Zéro veut dire « personne ne pousse ». C'est ce qui permet à toutes les
        // machines de voir le battant céder pendant qu'on s'appuie dessus.
        private readonly SyncList<int> _pushes = new();

        private readonly HashSet<int> _occupied = new();

        private MovableWall[] _walls = Array.Empty<MovableWall>();
        private float[] _nextSwingAllowedAt = Array.Empty<float>();

        // Effort mesuré par l'hôte, et lui seul : un client qui répéterait son
        // intention plus vite ne pousserait pas plus fort pour autant.
        private float[] _effort = Array.Empty<float>();
        private float[] _pushIntentAt = Array.Empty<float>();
        private int[] _pushTarget = Array.Empty<int>();

        // Tant que ce délai court, l'effort ne redescend pas : le mur encaisse le
        // coup et vibre encore. C'est ce qui laisse enchaîner les frappes.
        private float[] _punchHoldUntil = Array.Empty<float>();

        // Animation du battant, propre à chaque machine et jamais répliquée : elle
        // rattrape la pose reçue, elle ne la décide pas.
        private int[] _shownPose = Array.Empty<int>();
        private Vector3[] _swingHinge = Array.Empty<Vector3>();
        private Vector3[] _swingFromPosition = Array.Empty<Vector3>();
        private Quaternion[] _swingFromRotation = Array.Empty<Quaternion>();
        private float[] _swingAngle = Array.Empty<float>();
        private float[] _swingProgress = Array.Empty<float>();
        private int[] _shownPushTarget = Array.Empty<int>();
        private float[] _shownEffort = Array.Empty<float>();
        private Vector3[] _pushHinge = Array.Empty<Vector3>();
        private float[] _pushAngle = Array.Empty<float>();

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
            _shownEffort = new float[walls.Length];
            _pushHinge = new Vector3[walls.Length];
            _pushAngle = new float[walls.Length];

            _shownPushTarget = new int[walls.Length];
            for (var index = 0; index < walls.Length; index++)
                _shownPushTarget[index] = -1;
        }

        public override void OnStartServer()
        {
            base.OnStartServer();

            ResolveWalls();
            _nextSwingAllowedAt = new float[_walls.Length];
            _effort = new float[_walls.Length];
            _pushIntentAt = new float[_walls.Length];
            _punchHoldUntil = new float[_walls.Length];
            _pushTarget = new int[_walls.Length];
            for (var index = 0; index < _walls.Length; index++)
                _pushTarget[index] = -1;

            _occupied.Clear();
            foreach (var slot in _blockedSlots)
                _occupied.Add(slot);

            _poses.Clear();
            _pushes.Clear();
            foreach (var wall in _walls)
            {
                var slot = SlotKey(wall.HomeFamily, wall.HomeSlotX, wall.HomeSlotY);
                _poses.Add(Pack(slot, 0));
                _pushes.Add(0);
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
            if (IsServerStarted)
                AdvancePushes();

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

                if (_swingProgress[index] < 1f)
                {
                    _swingProgress[index] = Mathf.Min(1f, _swingProgress[index] + Time.deltaTime / SwingSeconds);

                    var swing = Quaternion.AngleAxis(_swingAngle[index] * Ease(_swingProgress[index]), Vector3.up);
                    wall.transform.SetPositionAndRotation(
                        _swingHinge[index] + swing * (_swingFromPosition[index] - _swingHinge[index]),
                        swing * _swingFromRotation[index]);
                    continue;
                }

                ShowPush(index, wall, pose);
            }
        }

        /// <summary>
        /// Pose le mur à l'endroit où la poussée en cours l'a amené. L'effort reçu est
        /// lissé sur place : il arrive par paliers, et un vantail de pierre ne
        /// progresse pas par à-coups.
        /// </summary>
        private void ShowPush(int index, MovableWall wall, int pose)
        {
            var packed = index < _pushes.Count ? _pushes[index] : 0;
            var target = packed == 0 ? -1 : PushSlotOf(packed);
            var wanted = packed == 0 ? 0f : PushPercentOf(packed) / 100f;

            if (target >= 0 && target != _shownPushTarget[index])
            {
                if (TryFindHinge(SlotOf(pose), target, out var hinge))
                {
                    _shownPushTarget[index] = target;
                    _pushHinge[index] = NodePosition(hinge);
                    _pushAngle[index] = QuarterTurnAngle(SlotOf(pose), target, hinge);
                }
                else
                {
                    wanted = 0f;
                }
            }
            else if (target < 0)
            {
                // Le mur a été lâché : il revient, il ne se fige pas en biais.
                wanted = 0f;
            }

            _shownEffort[index] = Mathf.Lerp(
                _shownEffort[index], wanted, 1f - Mathf.Exp(-PushSmoothing * Time.deltaTime));

            var basePosition = SlotCenter(SlotOf(pose));
            var baseRotation = Quaternion.AngleAxis(90f * TurnsOf(pose), Vector3.up);

            if (_shownEffort[index] < 0.002f)
            {
                _shownEffort[index] = 0f;
                _shownPushTarget[index] = -1;
                if (wall.transform.position != basePosition)
                    wall.transform.SetPositionAndRotation(basePosition, baseRotation);
                return;
            }

            var rotation = Quaternion.AngleAxis(_pushAngle[index] * Ease(_shownEffort[index]), Vector3.up);
            wall.transform.SetPositionAndRotation(
                _pushHinge[index] + rotation * (basePosition - _pushHinge[index]),
                rotation * baseRotation);
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

            var target = SlotCenter(SlotOf(pose));
            var targetRotation = Quaternion.AngleAxis(90f * TurnsOf(pose), Vector3.up);

            // Une poussée qui aboutit a déjà amené le battant au bout de sa course :
            // rejouer le mouvement le ferait repartir en arrière d'un coup.
            if (_shownPushTarget[index] == SlotOf(pose))
            {
                _shownPushTarget[index] = -1;
                _shownEffort[index] = 0f;
                _walls[index].transform.SetPositionAndRotation(target, targetRotation);
                _swingProgress[index] = 1f;
                return;
            }

            if (previous < 0 || !TryFindHinge(SlotOf(previous), SlotOf(pose), out var hinge))
            {
                _walls[index].transform.SetPositionAndRotation(target, targetRotation);
                _swingProgress[index] = 1f;
                return;
            }

            _swingHinge[index] = NodePosition(hinge);
            _swingFromPosition[index] = SlotCenter(SlotOf(previous));
            _swingFromRotation[index] = Quaternion.AngleAxis(90f * TurnsOf(previous), Vector3.up);
            _swingAngle[index] = Mathf.DeltaAngle(90f * TurnsOf(previous), 90f * TurnsOf(pose));
            _swingProgress[index] = 0f;
            _shownEffort[index] = 0f;
            _shownPushTarget[index] = -1;
        }

        /// <summary>Départ et arrivée mous, plein élan au milieu : le poids d'un vantail de pierre.</summary>
        private static float Ease(float t)
        {
            return t * t * t * (t * (t * 6f - 15f) + 10f);
        }

        /// <summary>
        /// Intention de pousser un mur à l'épaule, répétée par le client tant qu'il
        /// avance contre lui. L'hôte ne fait qu'enregistrer l'intention : c'est lui
        /// qui mesure l'effort, à son propre rythme, donc répéter le message plus vite
        /// ne fait pas céder le mur plus tôt.
        /// </summary>
        [ServerRpc(RequireOwnership = false)]
        public void RequestWallPush(int wallId, NetworkConnection sender = null)
        {
            if (wallId < 0 || wallId >= _walls.Length || wallId >= _poses.Count)
                return;

            if (Time.time < _nextSwingAllowedAt[wallId])
                return;

            var pusher = sender?.FirstObject;
            if (pusher == null)
                return;

            var position = pusher.transform.position;
            var forward = pusher.transform.forward;

            // Contact à l'épaule, et non à bout de bras : on doit être sur le mur.
            if (DistanceToWall(position, SlotCenter(SlotOf(_poses[wallId])), SlotAxis(FamilyOf(SlotOf(_poses[wallId])))) > PushReach)
                return;

            // Le joueur doit pousser vers quelque part : marcher le long d'un mur ne
            // le fait pas céder, seulement marcher dedans.
            if (!TryResolveTarget(wallId, forward, position, true, out var target))
            {
                _pushTarget[wallId] = -1;
                return;
            }

            // Changer de sens en cours de poussée remet l'effort à zéro.
            if (_pushTarget[wallId] != target)
            {
                _pushTarget[wallId] = target;
                _effort[wallId] = 0f;
            }

            _pushIntentAt[wallId] = Time.time;
        }

        /// <summary>
        /// Avance les efforts en cours, côté hôte uniquement. Peu importe d'où vient
        /// l'effort — épaule ou coup de poing — c'est le même compteur : un mur qu'on
        /// laisse retombe, un mur mené jusqu'au bout bascule d'un quart de tour.
        /// </summary>
        private void AdvancePushes()
        {
            for (var id = 0; id < _walls.Length && id < _pushes.Count; id++)
            {
                var target = _pushTarget[id];
                if (target < 0)
                    continue;

                if (Time.time - _pushIntentAt[id] <= IntentTimeout)
                    _effort[id] += Time.deltaTime / PushSeconds;
                else if (Time.time >= _punchHoldUntil[id])
                    _effort[id] -= Time.deltaTime / ReleaseSeconds;

                if (_effort[id] >= 1f)
                {
                    _effort[id] = 0f;
                    _pushTarget[id] = -1;
                    _punchHoldUntil[id] = 0f;
                    PublishPush(id, -1, 0f);
                    ApplyTurn(id, target);
                    continue;
                }

                if (_effort[id] <= 0f)
                {
                    _effort[id] = 0f;
                    _pushTarget[id] = -1;
                    _punchHoldUntil[id] = 0f;
                    PublishPush(id, -1, 0f);
                    continue;
                }

                PublishPush(id, target, _effort[id]);
            }
        }

        private void PublishPush(int id, int target, float effort)
        {
            var packed = target < 0
                ? 0
                : PackPush(target, Mathf.Clamp(Mathf.RoundToInt(effort * 100f / PushStep) * PushStep, 0, 100));

            if (_pushes[id] != packed)
                _pushes[id] = packed;
        }

        /// <summary>
        /// Ébranle un mur d'un coup de poing. Le coup ne fait pas basculer le mur : il
        /// verse un tiers de la course dans le même effort que la poussée à l'épaule,
        /// et laisse le battant ébranlé un instant avant qu'il ne retombe. Trois coups
        /// enchaînés l'ouvrent donc, un coup isolé jamais — c'est là qu'on sent le
        /// poids de la pierre. Appelé uniquement côté serveur, depuis la validation
        /// d'une frappe : le client n'a désigné ni le mur, ni le gond, ni le sens.
        /// </summary>
        /// <param name="wall">Mur touché sur la copie serveur du décor.</param>
        /// <param name="puncherPosition">Position répliquée du frappeur.</param>
        /// <param name="puncherForward">Regard du frappeur, qui donne le sens.</param>
        /// <param name="impactPoint">Point touché, qui désigne le battant donc le gond.</param>
        /// <returns>Vrai si le coup a porté sur le mur.</returns>
        public bool TryPunch(MovableWall wall, Vector3 puncherPosition, Vector3 puncherForward, Vector3 impactPoint)
        {
            if (!IsServerStarted || wall == null)
                return false;

            var id = wall.Id;
            if (id < 0 || id >= _walls.Length || id >= _poses.Count || _walls[id] != wall)
                return false;

            if (Time.time < _nextSwingAllowedAt[id])
                return false;

            var slot = SlotOf(_poses[id]);
            if (DistanceToWall(puncherPosition, SlotCenter(slot), SlotAxis(FamilyOf(slot))) > ServerReach)
                return false;

            // Un coup de poing porte même donné de biais, là où la poussée à l'épaule
            // exige de pousser franchement vers quelque part.
            if (!TryResolveTarget(id, puncherForward, impactPoint, false, out var target))
                return false;

            // Frapper l'autre battant repart de zéro : on ne cumule pas deux efforts
            // qui tirent le mur dans deux sens opposés.
            if (_pushTarget[id] != target)
            {
                _pushTarget[id] = target;
                _effort[id] = 0f;
            }

            _effort[id] += PunchEffort;
            _punchHoldUntil[id] = Time.time + PunchHoldSeconds;
            return true;
        }

        /// <summary>
        /// Arête vers laquelle ce mur basculerait sous une poussée venue de
        /// <paramref name="contactPoint"/> et dirigée par <paramref name="pushForward"/>.
        ///
        /// Le gond est le bout le plus éloigné du contact : on pousse le battant,
        /// jamais la charnière. Des deux quarts de tour possibles autour de ce gond,
        /// on garde celui qui emmène le battant du côté où l'on pousse.
        /// </summary>
        private bool TryResolveTarget(int id, Vector3 pushForward, Vector3 contactPoint, bool requireForward, out int target)
        {
            target = -1;

            var slot = SlotOf(_poses[id]);
            EdgeNodes(FamilyOf(slot), XOf(slot), YOf(slot), out var nodeA, out var nodeB);

            var worldA = NodePosition(nodeA);
            var worldB = NodePosition(nodeB);
            var hingeIsA = (contactPoint - worldA).sqrMagnitude > (contactPoint - worldB).sqrMagnitude;
            var hinge = hingeIsA ? nodeA : nodeB;
            var leaf = hingeIsA ? nodeB : nodeA;
            var leafWorld = hingeIsA ? worldB : worldA;

            var arm = leaf - hinge;
            var forward = pushForward;
            forward.y = 0f;
            forward.Normalize();

            var bestScore = requireForward ? 0f : float.NegativeInfinity;

            for (var sign = -1; sign <= 1; sign += 2)
            {
                // Quart de tour dans le repère de la grille, des deux côtés.
                var rotated = sign > 0
                    ? new Vector2Int(-arm.y, arm.x)
                    : new Vector2Int(arm.y, -arm.x);

                var candidate = SlotForEdge(hinge, hinge + rotated);
                if (candidate < 0 || _occupied.Contains(candidate) || !IsAnchoredToHome(_walls[id], candidate))
                    continue;

                var score = Vector3.Dot(forward, NodePosition(hinge + rotated) - leafWorld);
                if (score <= bestScore)
                    continue;

                bestScore = score;
                target = candidate;
            }

            return target >= 0;
        }

        /// <summary>
        /// Pose le mur sur son arête d'arrivée, après les dernières vérifications que
        /// l'hôte doit refaire au moment où le mur bouge vraiment : la carte a pu
        /// changer depuis le début d'une poussée.
        /// </summary>
        private bool ApplyTurn(int id, int target)
        {
            var pose = _poses[id];
            var slot = SlotOf(pose);
            var wall = _walls[id];

            if (_occupied.Contains(target))
                return false;

            if (!IsAnchoredToHome(wall, target))
                return false;

            if (!IsClearOfPlayers(SlotCenter(target), SlotAxis(FamilyOf(target))))
                return false;

            if (!TryFindHinge(slot, target, out var hinge))
                return false;

            // Le sens de rotation se relit sur la géométrie et non sur le signe de
            // grille : les deux axes du plan sont retournés à l'export du FBX.
            var turn = QuarterTurnAngle(slot, target, hinge) > 0f ? 1 : -1;

            _occupied.Remove(slot);
            _occupied.Add(target);
            _poses[id] = Pack(target, TurnsOf(pose) + turn);
            _nextSwingAllowedAt[id] = Time.time + SwingCooldown;
            return true;
        }

        /// <summary>
        /// Vrai si l'arête touche encore un des deux nœuds de l'arête d'origine du
        /// mur. C'est ce qui garde chaque mur accroché à son embrasure : il pivote
        /// autour de l'un ou l'autre de ses bouts, il ne se promène pas. Sans cette
        /// borne, des coups répétés le font marcher d'arête en arête jusqu'à finir
        /// hors de vue derrière le labyrinthe, et le joueur voit un mur disparaître.
        /// </summary>
        private static bool IsAnchoredToHome(MovableWall wall, int slot)
        {
            EdgeNodes(wall.HomeFamily, wall.HomeSlotX, wall.HomeSlotY, out var homeA, out var homeB);
            EdgeNodes(FamilyOf(slot), XOf(slot), YOf(slot), out var first, out var second);

            return first == homeA || first == homeB || second == homeA || second == homeB;
        }

        /// <summary>Angle monde du quart de tour qui mène d'une arête à l'autre autour de leur gond.</summary>
        private float QuarterTurnAngle(int fromSlot, int toSlot, Vector2Int hinge)
        {
            EdgeNodes(FamilyOf(fromSlot), XOf(fromSlot), YOf(fromSlot), out var fromA, out var fromB);
            EdgeNodes(FamilyOf(toSlot), XOf(toSlot), YOf(toSlot), out var toA, out var toB);

            var hingeWorld = NodePosition(hinge);
            var fromLeaf = NodePosition(fromA == hinge ? fromB : fromA);
            var toLeaf = NodePosition(toA == hinge ? toB : toA);

            return Vector3.SignedAngle(fromLeaf - hingeWorld, toLeaf - hingeWorld, Vector3.up);
        }

        /// <summary>Effort visible sur un mur, de 0 à 1. Sert au retour d'écran du pousseur.</summary>
        public float EffortFor(int wallId)
        {
            if (wallId < 0 || wallId >= _pushes.Count)
                return 0f;

            var packed = _pushes[wallId];
            return packed == 0 ? 0f : PushPercentOf(packed) / 100f;
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

        // Poussée répliquée : l'arête visée et l'effort en pourcents dans un entier.
        // Zéro veut dire « aucune poussée » — l'arête 0 est sur le pourtour de la map,
        // elle n'est jamais une arrivée possible.
        private static int PackPush(int slot, int percent) => slot * 128 + percent;

        private static int PushSlotOf(int packed) => packed / 128;

        private static int PushPercentOf(int packed) => packed % 128;

        private static int FamilyOf(int slot) => slot / 1_000_000;

        private static int XOf(int slot) => slot % 1_000_000 / 1_000;

        private static int YOf(int slot) => slot % 1_000;
    }
}
