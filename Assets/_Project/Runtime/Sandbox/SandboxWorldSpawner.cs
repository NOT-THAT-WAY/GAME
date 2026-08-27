using System.Collections.Generic;
using FishNet.Managing;
using FishNet.Object;
using FishNet.Transporting;
using UnityEngine;

namespace NotThatWay.Game.Sandbox
{
    /// <summary>Fait apparaître le lot fixe de cailloux et l'unique trophée du sandbox.</summary>
    [DisallowMultipleComponent]
    public sealed class SandboxWorldSpawner : MonoBehaviour
    {
        [SerializeField] private NetworkObject _rockPrefab;
        [SerializeField] private NetworkObject _trophyPrefab;
        [SerializeField] private NetworkObject _oilCanPrefab;
        [SerializeField] private Vector3[] _rockSpawnPositions = System.Array.Empty<Vector3>();
        [SerializeField] private Vector3[] _oilCanSpawnPositions = System.Array.Empty<Vector3>();
        [SerializeField] private Vector3 _trophySpawnPosition;

        private readonly List<NetworkObject> _spawned = new();
        private NetworkManager _networkManager;

        private void Awake()
        {
            _networkManager = GetComponentInParent<NetworkManager>();
            if (_networkManager == null)
                _networkManager = FindFirstObjectByType<NetworkManager>();
            if (_networkManager == null)
            {
                Debug.LogError("[GAME-SANDBOX] NetworkManager introuvable pour les objets.", this);
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
            if (state.ConnectionState == LocalConnectionState.Stopped)
            {
                _spawned.Clear();
                return;
            }
            if (state.ConnectionState != LocalConnectionState.Started || _spawned.Count != 0)
                return;
            if (_rockPrefab == null || _trophyPrefab == null || _oilCanPrefab == null)
            {
                Debug.LogError("[GAME-SANDBOX] Prefabs de caillou/trophée/bidon absents.", this);
                return;
            }

            for (var index = 0; index < _rockSpawnPositions.Length; index++)
                Spawn(_rockPrefab, _rockSpawnPositions[index], $"rock-{index}");
            for (var index = 0; index < _oilCanSpawnPositions.Length; index++)
                Spawn(_oilCanPrefab, _oilCanSpawnPositions[index], $"oilcan-{index}");
            Spawn(_trophyPrefab, _trophySpawnPosition, "trophy");
            Debug.Log(
                $"[GAME-SANDBOX] objects_ready rocks={_rockSpawnPositions.Length} " +
                $"oilcans={_oilCanSpawnPositions.Length} trophy=1.",
                this);
        }

        private void Spawn(NetworkObject prefab, Vector3 position, string label)
        {
            var instance = Instantiate(prefab, position, Quaternion.identity);
            instance.name = $"Sandbox_{label}";
            _networkManager.ServerManager.Spawn(instance);
            _spawned.Add(instance);
        }
    }
}
