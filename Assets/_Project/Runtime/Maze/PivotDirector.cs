using System;
using FishNet.Connection;
using FishNet.Object;
using FishNet.Object.Synchronizing;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Détient l'orientation de tous les pivots de la map et la réplique.
    ///
    /// Conformément aux règles d'architecture du concept, ce qui circule sur le
    /// réseau est un état discret par pivot — un quart de tour parmi quatre — et
    /// jamais le transform d'un mur image par image. La rotation visible n'est
    /// qu'une transition locale entre deux états valides, donc deux machines qui
    /// affichent des angles intermédiaires différents restent d'accord sur le
    /// labyrinthe. C'est l'hôte qui valide la poussée.
    /// </summary>
    public sealed class PivotDirector : NetworkBehaviour
    {
        /// <summary>Portée du rayon de poussée, côté joueur. Le couloir fait 2,50 m.</summary>
        public const float PushReach = 2.4f;

        private const float QuarterTurnSeconds = 0.35f;
        private const float PushCooldown = 0.45f;

        // Tolérance ajoutée à la portée pour la validation serveur : le client a
        // bougé depuis l'envoi, et la latence ne doit pas annuler une poussée
        // légitime. Assez serré pour qu'on ne tourne pas un pivot d'un couloir voisin.
        private const float ServerReachTolerance = 1.5f;

        private readonly SyncList<byte> _orientations = new();
        private Transform[] _pivots = Array.Empty<Transform>();

        // Pose de repos relevée à la résolution, et non supposée à l'identité. Les
        // objets `Pivot_*` sortent du FBX avec la conversion d'axes Blender portée par
        // le nœud lui-même — une rotation de -90° en x. Leur imposer un lacet pur les
        // couchait par terre dès la première image, collider compris, donc sans qu'on
        // ait rien poussé. Le quart de tour se compose désormais par-dessus cette pose.
        private Quaternion[] _restRotations = Array.Empty<Quaternion>();
        private float[] _nextPushAllowedAt = Array.Empty<float>();

        /// <summary>
        /// Les pivots sont retrouvés dans la scène et triés par leur index, posé à la
        /// génération. Aucune référence n'est sérialisée : le director est un prefab
        /// spawné par l'hôte, il ne peut donc pas pointer des objets de scène.
        /// </summary>
        private void ResolvePivots()
        {
            var walls = FindObjectsByType<PivotWall>(FindObjectsSortMode.None);
            Array.Sort(walls, (left, right) => left.Index.CompareTo(right.Index));

            _pivots = new Transform[walls.Length];
            _restRotations = new Quaternion[walls.Length];
            for (var index = 0; index < walls.Length; index++)
            {
                _pivots[index] = walls[index].transform;
                _restRotations[index] = walls[index].transform.localRotation;
            }
        }

        public override void OnStartServer()
        {
            base.OnStartServer();

            ResolvePivots();
            _nextPushAllowedAt = new float[_pivots.Length];
            _orientations.Clear();
            for (var index = 0; index < _pivots.Length; index++)
                _orientations.Add(0);

            Debug.Log($"[GAME-PIVOT] {_pivots.Length} pivot(s) sous autorité de l'hôte.");
        }

        public override void OnStartClient()
        {
            base.OnStartClient();

            // L'hôte a déjà résolu la liste en démarrant le serveur.
            if (_pivots.Length == 0)
                ResolvePivots();

            Debug.Log($"[GAME-PIVOT] {_pivots.Length} pivot(s) trouvé(s) dans la scène, état reçu pour {_orientations.Count}.");
        }

        private void Update()
        {
            // Chaque machine rejoue la même cible : l'angle affiché rattrape l'état
            // répliqué, sans que personne n'envoie d'angle.
            var count = Mathf.Min(_pivots.Length, _orientations.Count);
            for (var index = 0; index < count; index++)
            {
                var pivot = _pivots[index];
                if (pivot == null)
                    continue;

                // Lacet monde posé sur la pose de repos : la racine de la map est à
                // l'identité, donc c'est bien le quart de tour attendu autour de la
                // verticale, et le bras reste debout.
                var target = Quaternion.Euler(0f, _orientations[index] * 90f, 0f) * _restRotations[index];
                pivot.localRotation = Quaternion.RotateTowards(
                    pivot.localRotation, target, 90f / QuarterTurnSeconds * Time.deltaTime);
            }
        }

        /// <summary>
        /// Demande un quart de tour. <paramref name="positiveTorque"/> vient du signe
        /// du couple calculé par le pousseur : le mur part dans le sens où on appuie.
        /// </summary>
        [ServerRpc(RequireOwnership = false)]
        public void RequestPush(int index, bool positiveTorque, NetworkConnection sender = null)
        {
            if (index < 0 || index >= _pivots.Length || index >= _orientations.Count)
            {
                HumanSmokeTestMode.LogEventOnce(
                    "pivot_rejected_server_invalid_index",
                    "pivot_rejected_server",
                    $"reason=invalid_index index={index}");
                return;
            }

            if (Time.time < _nextPushAllowedAt[index])
                return;

            // L'hôte ne fait tourner que ce que le demandeur pouvait atteindre.
            var pusher = sender?.FirstObject;
            if (pusher == null)
            {
                HumanSmokeTestMode.LogEventOnce(
                    "pivot_rejected_server_no_pusher",
                    "pivot_rejected_server",
                    "reason=no_pusher");
                return;
            }

            var offset = pusher.transform.position - _pivots[index].position;
            offset.y = 0f;
            if (offset.magnitude > PushReach + ServerReachTolerance)
            {
                HumanSmokeTestMode.LogEventOnce(
                    "pivot_rejected_server_out_of_reach",
                    "pivot_rejected_server",
                    $"reason=out_of_reach distance={offset.magnitude:F2}");
                return;
            }

            _nextPushAllowedAt[index] = Time.time + PushCooldown;
            _orientations[index] = (byte)((_orientations[index] + (positiveTorque ? 1 : 3)) % 4);
            HumanSmokeTestMode.LogEvent(
                "pivot_turned",
                $"index={index} orientation={_orientations[index]}");
        }
    }
}
