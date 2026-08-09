using FishNet.Managing;
using FishNet.Object;
using FishNet.Transporting;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>Spawn réseau reproductible du directeur M1 généré en prefab.</summary>
    [DisallowMultipleComponent]
    public sealed class M1WallAuthoritySpawner : MonoBehaviour
    {
        [SerializeField] private NetworkObject _authorityPrefab;

        private NetworkManager _networkManager;
        private NetworkObject _spawned;

        private void Awake()
        {
            _networkManager = GetComponentInParent<NetworkManager>();
            if (_networkManager == null)
                _networkManager = FindFirstObjectByType<NetworkManager>();
            if (_networkManager == null)
            {
                Debug.LogError("[GAME-M1-WALL] NetworkManager introuvable.");
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
            if (state.ConnectionState == LocalConnectionState.Stopped)
            {
                _spawned = null;
                return;
            }
            if (state.ConnectionState != LocalConnectionState.Started || _spawned != null)
                return;
            if (_authorityPrefab == null)
            {
                Debug.LogError("[GAME-M1-WALL] Prefab d'autorité absent.");
                return;
            }

            _spawned = Instantiate(_authorityPrefab);
            _networkManager.ServerManager.Spawn(_spawned);
        }
    }
}
