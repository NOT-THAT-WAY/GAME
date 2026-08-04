using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Caméra de la scène utilisée avant l'apparition du joueur local. Le
    /// <see cref="PlayerMotor"/> la retrouve par ce marqueur et l'éteint pour
    /// éviter deux caméras et deux AudioListener actifs en même temps.
    /// </summary>
    public sealed class SpectatorCamera : MonoBehaviour
    {
    }
}
