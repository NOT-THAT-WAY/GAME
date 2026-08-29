using System;

namespace NotThatWay.Game.Sandbox
{
    public enum SlingshotActionKind : byte
    {
        None = 0,
        /// <summary>Tap du bouton lance-pierre : le prendre (poche ou sol) ou, en main, charger un caillou.</summary>
        TakeOrLoad = 1,
        /// <summary>Bouton lance-pierre maintenu assez longtemps avec l'arme en main : la lâcher.</summary>
        Drop = 2,
        /// <summary>Bouton de tir relâché avec l'arme en main : tirer à la puissance chargée.</summary>
        Fire = 3
    }

    /// <summary>Entrées d'un tick, déjà filtrées par l'hôte (vie, objet actif).</summary>
    public readonly struct SlingshotTickInput
    {
        public SlingshotTickInput(
            bool slingshotPressed,
            bool slingshotHeld,
            bool firePressed,
            bool fireHeld,
            bool inHand)
        {
            SlingshotPressed = slingshotPressed;
            SlingshotHeld = slingshotHeld;
            FirePressed = firePressed;
            FireHeld = fireHeld;
            InHand = inHand;
        }

        public bool SlingshotPressed { get; }
        public bool SlingshotHeld { get; }
        public bool FirePressed { get; }
        public bool FireHeld { get; }
        public bool InHand { get; }
    }

    public readonly struct SlingshotTickResult
    {
        public SlingshotTickResult(SlingshotActionKind action, int powerPermille, int chargePermille)
        {
            Action = action;
            PowerPermille = powerPermille;
            ChargePermille = chargePermille;
        }

        public SlingshotActionKind Action { get; }
        /// <summary>Puissance du tir émis ce tick, sinon 0.</summary>
        public int PowerPermille { get; }
        /// <summary>Avancement de la charge en cours après ce tick, pour l'affichage.</summary>
        public int ChargePermille { get; }
    }

    /// <summary>
    /// Machine pure du lance-pierre, un pas par tick de commande autoritaire :
    /// distingue tap et maintien du bouton lance-pierre, mesure la charge du
    /// tir en ticks et la convertit en puissance bornée. Elle ne connaît ni
    /// l'inventaire ni l'énergie : l'hôte applique ou refuse l'action émise.
    /// </summary>
    public sealed class SandboxSlingshotModel
    {
        public const int PermilleScale = 1000;

        private readonly uint _dropHoldTicks;
        private readonly uint _chargeTicks;
        private readonly int _minimumPowerPermille;

        private uint _slingshotHeldTicks;
        private bool _slingshotHoldConsumed;
        private uint _chargeTicksElapsed;
        private bool _charging;

        public SandboxSlingshotModel(uint dropHoldTicks, uint chargeTicks, int minimumPowerPermille)
        {
            if (dropHoldTicks == 0u)
                throw new ArgumentOutOfRangeException(nameof(dropHoldTicks));
            if (chargeTicks == 0u)
                throw new ArgumentOutOfRangeException(nameof(chargeTicks));
            if (minimumPowerPermille < 1 || minimumPowerPermille > PermilleScale)
                throw new ArgumentOutOfRangeException(nameof(minimumPowerPermille));
            _dropHoldTicks = dropHoldTicks;
            _chargeTicks = chargeTicks;
            _minimumPowerPermille = minimumPowerPermille;
        }

        public static SandboxSlingshotModel FromConfig(SandboxGameplayConfig config) => new(
            config.SlingshotDropHoldTicks,
            config.SlingshotChargeTicks,
            config.SlingshotMinimumPowerPermille);

        public bool IsCharging => _charging;

        /// <summary>Avancement de la charge en cours, 0 hors charge.</summary>
        public int ChargePermille => _charging
            ? (int)Math.Min(PermilleScale, _chargeTicksElapsed * (long)PermilleScale / _chargeTicks)
            : 0;

        public SlingshotTickResult Advance(SlingshotTickInput input)
        {
            var action = SlingshotActionKind.None;
            var power = 0;

            // --- Bouton lance-pierre : tap ou maintien -------------------------
            if (!input.InHand)
            {
                // Sans arme en main, l'appui agit tout de suite (poche ou sol) et
                // le maintien qui suit ne doit pas lâcher l'arme à peine prise.
                if (input.SlingshotPressed)
                {
                    action = SlingshotActionKind.TakeOrLoad;
                    _slingshotHoldConsumed = true;
                }
                _slingshotHeldTicks = input.SlingshotHeld ? _slingshotHeldTicks + 1u : 0u;
                if (!input.SlingshotHeld)
                    _slingshotHoldConsumed = false;
            }
            else if (input.SlingshotHeld)
            {
                if (input.SlingshotPressed && _slingshotHeldTicks == 0u)
                    _slingshotHoldConsumed = false;
                if (_slingshotHeldTicks < uint.MaxValue)
                    _slingshotHeldTicks++;
                if (!_slingshotHoldConsumed && _slingshotHeldTicks >= _dropHoldTicks)
                {
                    _slingshotHoldConsumed = true;
                    action = SlingshotActionKind.Drop;
                }
            }
            else
            {
                // Relâché : un appui court non consommé par le maintien est un tap.
                // Un appui-relâchement entre deux ticks arrive comme front seul.
                var tapped = input.SlingshotPressed
                    ? !_slingshotHoldConsumed || _slingshotHeldTicks == 0u
                    : _slingshotHeldTicks > 0u && !_slingshotHoldConsumed;
                if (tapped)
                    action = SlingshotActionKind.TakeOrLoad;
                _slingshotHeldTicks = 0u;
                _slingshotHoldConsumed = false;
            }

            // --- Tir : charge tant que le bouton est tenu, part au relâchement ----
            if (!input.InHand)
            {
                _charging = false;
                _chargeTicksElapsed = 0u;
            }
            else if (input.FireHeld)
            {
                _charging = true;
                if (_chargeTicksElapsed < _chargeTicks)
                    _chargeTicksElapsed++;
            }
            else if (_charging)
            {
                power = PowerFromCharge(_chargeTicksElapsed);
                _charging = false;
                _chargeTicksElapsed = 0u;
                if (action == SlingshotActionKind.None)
                    action = SlingshotActionKind.Fire;
                else
                    power = 0; // Le bouton lance-pierre prime ce tick ; le tir est perdu.
            }
            else if (input.FirePressed)
            {
                // Appui-relâchement dans le même tick : tir minimal immédiat.
                power = PowerFromCharge(0u);
                if (action == SlingshotActionKind.None)
                    action = SlingshotActionKind.Fire;
                else
                    power = 0;
            }

            return new SlingshotTickResult(action, power, ChargePermille);
        }

        public void Reset()
        {
            _slingshotHeldTicks = 0u;
            _slingshotHoldConsumed = false;
            _chargeTicksElapsed = 0u;
            _charging = false;
        }

        private int PowerFromCharge(uint chargeTicksElapsed)
        {
            var ratio = Math.Min(chargeTicksElapsed, _chargeTicks) * (long)(PermilleScale - _minimumPowerPermille);
            return _minimumPowerPermille + (int)(ratio / _chargeTicks);
        }
    }
}
