using System;
using FishNet.Managing;
using FishNet.Object;
using FishNet.Transporting;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Fait apparaître le <see cref="SimpleBot"/> dès que le serveur démarre, à
    /// l'emplacement libre choisi par <c>MazePlaytestBuild</c> devant la première
    /// entrée du labyrinthe.
    /// Même raisonnement que <see cref="PivotDirectorSpawner"/> : un NetworkObject
    /// de scène n'est pas répliqué dans nos scènes générées en batch, on passe
    /// donc par un prefab spawné.
    ///
    /// Sauf pendant un run automatisé : le bot frappe, pousse les murs et fait
    /// repartir des manches de son propre chef. Une gate qui compte des quarts
    /// de tour, des révisions et des poussées opposées mesure alors le bot
    /// autant que le scénario. Le banc humain et les captures de contrôle, eux,
    /// le gardent — c'est leur raison d'être.
    /// </summary>
    public sealed class SimpleBotSpawner : MonoBehaviour
    {
        [SerializeField] private NetworkObject _botPrefab;
        [SerializeField] private Vector3 _spawnPosition;
        [SerializeField] private Quaternion _spawnRotation = Quaternion.identity;

        private NetworkManager _networkManager;
        private NetworkObject _spawned;

        private void Awake()
        {
            _networkManager = GetComponentInParent<NetworkManager>();
            if (_networkManager == null)
                _networkManager = FindFirstObjectByType<NetworkManager>();

            if (_networkManager == null)
            {
                Debug.LogError("[GAME-BOT] NetworkManager introuvable : le bot n'apparaîtra pas.");
                return;
            }

            _networkManager.ServerManager.OnServerConnectionState += OnServerConnectionState;
        }

        private void OnDestroy()
        {
            if (_networkManager != null && _networkManager.ServerManager != null)
                _networkManager.ServerManager.OnServerConnectionState -= OnServerConnectionState;
        }

        private void OnServerConnectionState(ServerConnectionStateArgs state)
        {
            if (state.ConnectionState != LocalConnectionState.Started)
                return;

            if (M1AutomatedTestPlan.IsAutomatedRun(Environment.GetCommandLineArgs()))
            {
                Debug.Log(
                    "[GAME-BOT] Run automatisé : pas de bot d'entraînement, " +
                    "le banc mesuré ne contient que les joueurs du scénario.");
                return;
            }

            if (_botPrefab == null)
            {
                Debug.LogError("[GAME-BOT] Prefab du bot absent : le bot n'apparaîtra pas.");
                return;
            }

            if (_spawned != null)
                return;

            _spawned = Instantiate(_botPrefab, _spawnPosition, _spawnRotation);
            _networkManager.ServerManager.Spawn(_spawned);
            Debug.Log($"[GAME-BOT] Bot d'entraînement spawné en {_spawnPosition}.");
        }
    }
}
