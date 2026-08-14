using System;
using FishNet.Managing.Transporting;
using UnityEditor;
using UnityEngine;

namespace NotThatWay.Game.Editor
{
    internal static class FishNetBuildConfiguration
    {
        internal static void AddVersionHandshakeGuard(GameObject networkRoot)
        {
            if (networkRoot == null)
                throw new ArgumentNullException(nameof(networkRoot));

            // NetworkManager normally creates this component from Awake. Scene
            // builders run in Edit Mode, so create it now in order to serialize
            // the layer before the player starts.
            var transportManager = networkRoot.GetComponent<TransportManager>() ??
                networkRoot.AddComponent<TransportManager>();

            var guard = networkRoot.GetComponent<FishNetVersionHandshakeGuard>() ??
                networkRoot.AddComponent<FishNetVersionHandshakeGuard>();
            var serializedTransport = new SerializedObject(transportManager);
            var layerProperty = serializedTransport.FindProperty("_intermediateLayer");
            if (layerProperty == null)
                throw new InvalidOperationException("Champ FishNet _intermediateLayer introuvable.");

            layerProperty.objectReferenceValue = guard;
            serializedTransport.ApplyModifiedPropertiesWithoutUndo();
        }
    }
}
