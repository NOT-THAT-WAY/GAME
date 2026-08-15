using UnityEngine;

namespace NotThatWay.Game.Sandbox
{
    /// <summary>
    /// Zone de validation locale à la scène. Le trigger ne décide rien : il
    /// demande au composant joueur serveur de vérifier trophée, vie et manche.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(Collider))]
    public sealed class SandboxDepositZone : MonoBehaviour
    {
        public static Vector3 DepositedTrophyPosition { get; private set; }

        private void Awake()
        {
            DepositedTrophyPosition = transform.position + Vector3.up * 0.75f;
            var trigger = GetComponent<Collider>();
            trigger.isTrigger = true;
        }

        private void OnTriggerEnter(Collider other) => TryDeposit(other);
        private void OnTriggerStay(Collider other) => TryDeposit(other);

        private static void TryDeposit(Collider other)
        {
            if (other == null)
                return;
            var player = other.GetComponentInParent<SandboxPlayerGameplay>();
            if (player != null)
                player.TryDepositTrophyFromServer();
        }
    }
}
