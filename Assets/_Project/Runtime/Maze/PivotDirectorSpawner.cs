using FishNet.Managing;
using FishNet.Object;
using FishNet.Transporting;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Fait apparaître le <see cref="PivotDirector"/> dès que le serveur démarre.
    ///
    /// Le director pourrait vivre dans la scène, mais un NetworkObject de scène
    /// dépend d'un identifiant que l'éditeur n'attribue pas en mode batch, où nos
    /// scènes sont justement générées : il n'était alors jamais répliqué. Passer
    /// par un prefab spawné emprunte le même chemin que le prefab joueur, qui lui
    /// fonctionne.
    /// </summary>
    public sealed class PivotDirectorSpawner : MonoBehaviour
    {
        [SerializeField] private NetworkObject _directorPrefab;

        private NetworkManager _networkManager;
        private NetworkObject _spawned;

        private void Awake()
        {
            _networkManager = GetComponentInParent<NetworkManager>();
            if (_networkManager == null)
                _networkManager = FindFirstObjectByType<NetworkManager>();

            if (_networkManager == null)
            {
                Debug.LogError("[GAME-PIVOT] NetworkManager introuvable : les pivots ne tourneront pas.");
                return;
            }

            _networkManager.ServerManager.OnServerConnectionState += OnServerConnectionState;
        }

        private void OnDestroy()
        {
            if (_networkManager != null)
                _networkManager.ServerManager.OnServerConnectionState -= OnServerConnectionState;
        }

        private void OnServerConnectionState(ServerConnectionStateArgs state)
        {
            if (state.ConnectionState != LocalConnectionState.Started)
                return;

            if (_directorPrefab == null)
            {
                Debug.LogError("[GAME-PIVOT] Prefab du director absent : les pivots ne tourneront pas.");
                return;
            }

            if (_spawned != null)
                return;

            _spawned = Instantiate(_directorPrefab);
            _networkManager.ServerManager.Spawn(_spawned);
        }
    }
}
