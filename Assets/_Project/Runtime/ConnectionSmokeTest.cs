using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using FishNet.Broadcast;
using FishNet.Connection;
using FishNet.Managing;
using FishNet.Transporting;
using UnityEngine;

namespace NotThatWay.Game
{
    public struct ParticipantHello : IBroadcast
    {
        public string Name;
        public string Platform;
    }

    public struct ParticipantRoster : IBroadcast
    {
        public string Lines;
    }

    public sealed class ConnectionSmokeTest : MonoBehaviour
    {
        private const ushort DefaultPort = 7770;
        private readonly Dictionary<int, string> _serverParticipants = new();

        private NetworkManager _networkManager;
        private string _address = "127.0.0.1";
        private string _participantName;
        private string _requestedRole = "manual";
        private string _roster = "Pas encore connecté";
        private string _lastMessage = "Choisir Host sur une machine, puis Client sur les autres.";
        private ushort _port = DefaultPort;
        private bool _starting;

        private IEnumerator Start()
        {
            _participantName = Sanitize(SystemInfo.deviceName, "Player");
            ParseCommandLine(Environment.GetCommandLineArgs());

            _networkManager = GetComponent<NetworkManager>();
            if (_networkManager == null)
                _networkManager = FindFirstObjectByType<NetworkManager>();

            if (_networkManager == null)
            {
                _lastMessage = "ERREUR: NetworkManager introuvable.";
                Debug.LogError($"[GAME-CONNECTION] {_lastMessage}");
                yield break;
            }

            _networkManager.ServerManager.RegisterBroadcast<ParticipantHello>(OnParticipantHello);
            _networkManager.ClientManager.RegisterBroadcast<ParticipantRoster>(OnParticipantRoster);
            _networkManager.ServerManager.OnRemoteConnectionState += OnRemoteConnectionState;
            _networkManager.ClientManager.OnAuthenticated += OnClientAuthenticated;

            yield return null;

            if (_requestedRole != "manual")
                yield return StartRole(_requestedRole);
        }

        private void OnDestroy()
        {
            if (_networkManager == null || !_networkManager.Initialized)
                return;

            _networkManager.ServerManager.UnregisterBroadcast<ParticipantHello>(OnParticipantHello);
            _networkManager.ClientManager.UnregisterBroadcast<ParticipantRoster>(OnParticipantRoster);
            _networkManager.ServerManager.OnRemoteConnectionState -= OnRemoteConnectionState;
            _networkManager.ClientManager.OnAuthenticated -= OnClientAuthenticated;
        }

        private void ParseCommandLine(string[] arguments)
        {
            for (var index = 0; index < arguments.Length; index++)
            {
                ReadArgument(arguments, ref index, "--game-role", value => _requestedRole = value.ToLowerInvariant());
                ReadArgument(arguments, ref index, "--game-address", value => _address = value);
                ReadArgument(arguments, ref index, "--game-name", value => _participantName = Sanitize(value, _participantName));
                ReadArgument(arguments, ref index, "--game-port", value =>
                {
                    if (ushort.TryParse(value, out var parsed))
                        _port = parsed;
                });
            }

            if (_requestedRole != "host" && _requestedRole != "server" && _requestedRole != "client")
                _requestedRole = "manual";
        }

        private static void ReadArgument(string[] arguments, ref int index, string key, Action<string> apply)
        {
            var current = arguments[index];
            var prefix = key + "=";
            if (current.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            {
                apply(current.Substring(prefix.Length));
                return;
            }

            if (string.Equals(current, key, StringComparison.OrdinalIgnoreCase) && index + 1 < arguments.Length)
            {
                index++;
                apply(arguments[index]);
            }
        }

        private IEnumerator StartRole(string role)
        {
            if (_starting)
                yield break;

            _starting = true;
            _requestedRole = role;

            if (role == "host" || role == "server")
            {
                _lastMessage = $"Démarrage serveur sur le port {_port}...";
                Debug.Log($"[GAME-CONNECTION] {_lastMessage}");
                _networkManager.ServerManager.StartConnection(_port);

                var deadline = Time.realtimeSinceStartup + 10f;
                while (!_networkManager.ServerManager.Started && Time.realtimeSinceStartup < deadline)
                    yield return null;

                if (!_networkManager.ServerManager.Started)
                {
                    _lastMessage = "ERREUR: le serveur ne s'est pas lancé.";
                    Debug.LogError($"[GAME-CONNECTION] {_lastMessage}");
                    _starting = false;
                    yield break;
                }
            }

            if (role == "host" || role == "client")
            {
                var target = role == "host" ? "127.0.0.1" : _address;
                _lastMessage = $"Connexion client à {target}:{_port}...";
                Debug.Log($"[GAME-CONNECTION] {_lastMessage}");
                _networkManager.ClientManager.StartConnection(target, _port);
            }

            _starting = false;
        }

        private void StopAll()
        {
            if (_networkManager.ClientManager.Started)
                _networkManager.ClientManager.StopConnection();
            if (_networkManager.ServerManager.Started)
                _networkManager.ServerManager.StopConnection(true);

            _serverParticipants.Clear();
            _roster = "Pas encore connecté";
            _lastMessage = "Connexions arrêtées.";
        }

        private void OnClientAuthenticated()
        {
            var hello = new ParticipantHello
            {
                Name = Sanitize(_participantName, "Player"),
                Platform = Application.platform.ToString()
            };
            _networkManager.ClientManager.Broadcast(hello);
            _lastMessage = $"CONNECTÉ à {_address}:{_port}";
            Debug.Log($"[GAME-CONNECTION] Authenticated as {hello.Name} on {hello.Platform}.");
        }

        private void OnParticipantHello(NetworkConnection connection, ParticipantHello hello, Channel channel)
        {
            _serverParticipants[connection.ClientId] = $"{Sanitize(hello.Name, "Player")} — {Sanitize(hello.Platform, "Unknown")}";
            PublishRoster();
        }

        private void OnRemoteConnectionState(NetworkConnection connection, RemoteConnectionStateArgs state)
        {
            if (state.ConnectionState != RemoteConnectionState.Stopped)
                return;

            if (_serverParticipants.Remove(state.ConnectionId))
                PublishRoster();
        }

        private void PublishRoster()
        {
            var lines = _serverParticipants
                .OrderBy(pair => pair.Key)
                .Select(pair => $"#{pair.Key}  {pair.Value}");
            var roster = string.Join("\n", lines);
            _networkManager.ServerManager.Broadcast(new ParticipantRoster { Lines = roster });
            Debug.Log($"[GAME-CONNECTION] Roster updated ({_serverParticipants.Count} participant(s)).");
        }

        private void OnParticipantRoster(ParticipantRoster roster, Channel channel)
        {
            _roster = string.IsNullOrWhiteSpace(roster.Lines) ? "Connecté, roster vide" : roster.Lines;
        }

        private static string Sanitize(string value, string fallback)
        {
            if (string.IsNullOrWhiteSpace(value))
                return fallback;

            var cleaned = value.Replace("\n", " ").Replace("\r", " ").Trim();
            return cleaned.Length <= 40 ? cleaned : cleaned.Substring(0, 40);
        }

        private void OnGUI()
        {
            const float width = 620f;
            var height = Mathf.Min(560f, Screen.height - 32f);
            GUILayout.BeginArea(new Rect(16f, 16f, Mathf.Min(width, Screen.width - 32f), height), GUI.skin.box);
            GUILayout.Label("GAME — premier test réseau", HeaderStyle());
            GUILayout.Space(8f);

            var server = _networkManager != null && _networkManager.ServerManager.Started;
            var client = _networkManager != null && _networkManager.ClientManager.Started;
            var authenticated = client && _networkManager.ClientManager.Connection.IsAuthenticated;
            GUILayout.Label($"Serveur: {(server ? "STARTED" : "stopped")}   Client: {(authenticated ? "AUTHENTICATED" : client ? "starting" : "stopped")}");
            if (server)
                GUILayout.Label($"Connexions serveur: {_networkManager.ServerManager.Clients.Count}");

            GUILayout.Space(8f);
            GUI.enabled = !server && !client && !_starting;
            GUILayout.Label("Nom");
            _participantName = GUILayout.TextField(_participantName);
            GUILayout.Label("Adresse de l'hôte");
            _address = GUILayout.TextField(_address);
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("HOST", GUILayout.Height(38f)))
                StartCoroutine(StartRole("host"));
            if (GUILayout.Button("CLIENT", GUILayout.Height(38f)))
                StartCoroutine(StartRole("client"));
            if (GUILayout.Button("SERVER", GUILayout.Height(38f)))
                StartCoroutine(StartRole("server"));
            GUILayout.EndHorizontal();
            GUI.enabled = true;

            if (server || client)
            {
                if (GUILayout.Button("STOP", GUILayout.Height(30f)))
                    StopAll();
            }

            GUILayout.Space(12f);
            GUILayout.Label($"Port UDP: {_port}");
            GUILayout.Label(_lastMessage);
            GUILayout.Space(12f);
            GUILayout.Label("Participants reçus du serveur", HeaderStyle());
            GUILayout.TextArea(_roster, GUILayout.MinHeight(100f));
            GUILayout.Space(8f);
            GUILayout.Label("Succès = les trois noms apparaissent dans cette liste.");
            GUILayout.EndArea();
        }

        private static GUIStyle HeaderStyle()
        {
            var style = new GUIStyle(GUI.skin.label)
            {
                fontSize = 22,
                fontStyle = FontStyle.Bold,
                wordWrap = true
            };
            return style;
        }
    }
}
