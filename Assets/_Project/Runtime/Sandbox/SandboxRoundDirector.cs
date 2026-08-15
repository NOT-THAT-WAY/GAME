using System;
using System.Collections.Generic;
using FishNet.Connection;
using FishNet.Object;
using FishNet.Transporting;
using FishNet.Utility.Template;
using NotThatWay.Game.Simulation;
using UnityEngine;

namespace NotThatWay.Game.Sandbox
{
    /// <summary>
    /// Boucle minimale : attente, compte à rebours, 90 secondes de jeu, résultat,
    /// puis remise à zéro des ressources et objets. Le dépôt clôt la manche côté
    /// serveur ; le chrono sert de verdict sans vainqueur si personne n'y arrive.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class SandboxRoundDirector : TickNetworkBehaviour
    {
        private const uint SnapshotIntervalTicks = 60u;
        private readonly List<SandboxPlayerGameplay> _players = new(4);

        private SandboxRoundModel _model;
        private SandboxRoundState _observedState;
        private uint _lastSnapshotTick;

        public static SandboxRoundDirector ServerInstance { get; private set; }
        public static SandboxRoundDirector ObservedInstance { get; private set; }
        public SandboxRoundState ObservedState => IsServerStarted ? _model.State : _observedState;

        /// <summary>
        /// En dehors d'une scène sandbox, l'absence de director reste permissive
        /// pour ne pas casser les bancs historiques. Dès qu'une manche existe, la
        /// phase observée devient le contrat commun client/serveur.
        /// </summary>
        public static bool AllowsPlayerControl(bool asServer)
        {
            var instance = asServer ? ServerInstance : ObservedInstance;
            return instance == null ||
                   SandboxRoundRules.AllowsPlayerControl(instance.ObservedState.Phase);
        }

        private void Awake()
        {
            _model = new SandboxRoundModel(SandboxRoundConfig.Baseline60Hz);
            _observedState = _model.State;
            SetTickCallbacks(TickCallback.Tick);
        }

        public override void OnStartServer()
        {
            base.OnStartServer();
            if (TimeManager.TickRate != SandboxGameplayConfig.Baseline60Hz.TickRate)
            {
                throw new InvalidOperationException(
                    $"Le sandbox attend 60 Hz, reçu {TimeManager.TickRate} Hz.");
            }
            ServerInstance = this;
            PublishSnapshot();
        }

        public override void OnStopServer()
        {
            if (ServerInstance == this)
                ServerInstance = null;
            base.OnStopServer();
        }

        public override void OnStartClient()
        {
            base.OnStartClient();
            ObservedInstance = this;
        }

        public override void OnStopClient()
        {
            if (ObservedInstance == this)
                ObservedInstance = null;
            base.OnStopClient();
        }

        public override void OnSpawnServer(NetworkConnection connection)
        {
            base.OnSpawnServer(connection);
            if (connection == null)
                return;
            var state = _model.State;
            SendSnapshotTargetRpc(
                connection,
                state.Tick,
                (byte)state.Phase,
                state.PhaseTicksRemaining,
                state.RoundNumber,
                state.WinnerObjectId);
        }

        protected override void TimeManager_OnTick()
        {
            if (!IsServerStarted)
                return;
            SandboxPlayerGameplay.CopyServerInstances(_players);
            var events = _model.AdvanceTick(_players.Count);
            if ((events & SandboxRoundEvents.RoundCompleted) != 0)
                StopPlayersForResult();
            if ((events & SandboxRoundEvents.ResetRequested) != 0)
                ResetSandbox();
            if (events != SandboxRoundEvents.None ||
                TickMath.Elapsed(_lastSnapshotTick, _model.State.Tick) >= SnapshotIntervalTicks)
            {
                PublishSnapshot();
            }
        }

        public bool TryCompleteRound(int winnerObjectId)
        {
            if (!IsServerStarted || !_model.TryComplete(winnerObjectId))
                return false;
            StopPlayersForResult();
            PublishSnapshot();
            Debug.Log(
                $"[GAME-SANDBOX-ROUND] completed round={_model.State.RoundNumber} " +
                $"winner={winnerObjectId} tick={_model.State.Tick}.",
                this);
            return true;
        }

        private void StopPlayersForResult()
        {
            SandboxPlayerGameplay.CopyServerInstances(_players);
            for (var index = 0; index < _players.Count; index++)
                _players[index].StopForRoundResultFromServer();
        }

        private void ResetSandbox()
        {
            SandboxPlayerGameplay.CopyServerInstances(_players);
            for (var index = 0; index < _players.Count; index++)
                _players[index].ResetForRoundFromServer();
            SandboxCarryable.ResetAllFromServer();
            Debug.Log(
                $"[GAME-SANDBOX-ROUND] reset round={_model.State.RoundNumber} " +
                $"phase={_model.State.Phase} tick={_model.State.Tick}.",
                this);
        }

        private void PublishSnapshot()
        {
            if (!IsServerStarted)
                return;
            var state = _model.State;
            _lastSnapshotTick = state.Tick;
            ReceiveSnapshotObserversRpc(
                state.Tick,
                (byte)state.Phase,
                state.PhaseTicksRemaining,
                state.RoundNumber,
                state.WinnerObjectId,
                Channel.Reliable);
            ApplySnapshot(
                state.Tick,
                state.Phase,
                state.PhaseTicksRemaining,
                state.RoundNumber,
                state.WinnerObjectId);
        }

        [ObserversRpc(BufferLast = true, ExcludeServer = true)]
        private void ReceiveSnapshotObserversRpc(
            uint tick,
            byte phase,
            uint remaining,
            uint round,
            int winner,
            Channel channel = Channel.Reliable)
        {
            ApplySnapshot(tick, (SandboxRoundPhase)phase, remaining, round, winner);
        }

        [TargetRpc]
        private void SendSnapshotTargetRpc(
            NetworkConnection connection,
            uint tick,
            byte phase,
            uint remaining,
            uint round,
            int winner,
            Channel channel = Channel.Reliable)
        {
            ApplySnapshot(tick, (SandboxRoundPhase)phase, remaining, round, winner);
        }

        private void ApplySnapshot(
            uint tick,
            SandboxRoundPhase phase,
            uint remaining,
            uint round,
            int winner)
        {
            if (_observedState.Tick != 0u && TickMath.IsOlder(tick, _observedState.Tick))
                return;
            _observedState = new SandboxRoundState(tick, phase, remaining, round, winner);
        }

        private void OnGUI()
        {
            var state = ObservedState;
            var seconds = state.PhaseTicksRemaining /
                          (float)SandboxGameplayConfig.Baseline60Hz.TickRate;
            var text = state.Phase switch
            {
                SandboxRoundPhase.Waiting => "SANDBOX — attente d'un joueur",
                SandboxRoundPhase.Countdown => $"MANCHE {state.RoundNumber} — départ {Mathf.CeilToInt(seconds)}",
                SandboxRoundPhase.Playing => $"TROPHEE -> ZONE ORANGE   {seconds:F0} s",
                SandboxRoundPhase.Result when state.WinnerObjectId >= 0 =>
                    $"TROPHEE DEPOSE — joueur {state.WinnerObjectId}",
                _ => "TEMPS ECOULE"
            };
            const float width = 430f;
            GUILayout.BeginArea(
                new Rect((Screen.width - width) * 0.5f, 16f, width, 42f),
                GUI.skin.box);
            GUILayout.Label(text);
            GUILayout.EndArea();
        }
    }
}
