using System;
using System.Collections.Generic;
using NotThatWay.Game.PlayerSimulation;
using NotThatWay.Game.Simulation;

namespace NotThatWay.Game.PlayerNetwork
{
    public enum M1AutomatedPlayerProfile : byte
    {
        None = 0,
        ClearSweep = 1,
        InteractAfter120 = 2,
        InteractAfter180 = 3,

        /// <summary>Accompagne le battant vers l'ouest en poussant.</summary>
        PushLeft = 4,

        /// <summary>Accompagne le battant vers l'est en poussant.</summary>
        PushRight = 5,

        /// <summary>
        /// Pousse vers l'ouest sans accompagner ni relâcher. Destiné au face à
        /// face : quand les couples s'opposent, le battant est figé, donc il n'y
        /// a pas de battant qui s'écarte à suivre et aucun glissement à craindre.
        /// Le pousseur garde la pleine amplitude, ce qui lui permet de revenir au
        /// contact après le rebond — un profil d'accompagnement, lui, se fait
        /// écarter radialement et ne sait pas se rattraper.
        /// </summary>
        PressLeft = 6,

        /// <summary>Symétrique de <see cref="PressLeft"/>, vers l'est.</summary>
        PressRight = 7,

        /// <summary>
        /// Régression bout-en-bout du sandbox : attend la manche, rejoint le
        /// trophée, le ramasse puis le rapporte à la zone orange.
        /// </summary>
        SandboxTrophyRun = 8,

        /// <summary>Cible immobile au nord du battant pour le test de projectile.</summary>
        SandboxRockTarget = 9,

        /// <summary>Ramasse un caillou puis le lance sur SandboxRockTarget.</summary>
        SandboxRockThrower = 10,

        /// <summary>Se place à portée puis porte quatre coups autoritaires.</summary>
        SandboxPuncher = 11
    }

    /// <summary>
    /// Source déterministe réservée aux builds Development du banc M1. Elle injecte
    /// les mêmes commandes par tick que le chemin clavier, sans contourner Replicate.
    /// </summary>
    public readonly struct M1AutomatedCommandSource
    {
        private const string ArgumentName = "--m1-auto-player";

        public M1AutomatedCommandSource(
            M1AutomatedPlayerProfile profile,
            bool wasSpecified = true)
        {
            Profile = profile;
            WasSpecified = wasSpecified;
        }

        public M1AutomatedPlayerProfile Profile { get; }
        public bool Enabled => Profile != M1AutomatedPlayerProfile.None;
        public bool WasSpecified { get; }

        public string Name
        {
            get
            {
                switch (Profile)
                {
                    case M1AutomatedPlayerProfile.ClearSweep:
                        return "clear-sweep";
                    case M1AutomatedPlayerProfile.InteractAfter120:
                        return "interact-120";
                    case M1AutomatedPlayerProfile.InteractAfter180:
                        return "interact-180";
                    case M1AutomatedPlayerProfile.PushLeft:
                        return "push-left";
                    case M1AutomatedPlayerProfile.PushRight:
                        return "push-right";
                    case M1AutomatedPlayerProfile.PressLeft:
                        return "press-left";
                    case M1AutomatedPlayerProfile.PressRight:
                        return "press-right";
                    case M1AutomatedPlayerProfile.SandboxTrophyRun:
                        return "sandbox-trophy-run";
                    case M1AutomatedPlayerProfile.SandboxRockTarget:
                        return "sandbox-rock-target";
                    case M1AutomatedPlayerProfile.SandboxRockThrower:
                        return "sandbox-rock-thrower";
                    case M1AutomatedPlayerProfile.SandboxPuncher:
                        return "sandbox-puncher";
                    default:
                        return "none";
                }
            }
        }

        public PlayerCommand CreateCommand(uint simulationTick)
        {
            switch (Profile)
            {
                case M1AutomatedPlayerProfile.ClearSweep:
                    return new PlayerCommand(
                        simulationTick,
                        0,
                        simulationTick <= 45u ? (sbyte)127 : (sbyte)0,
                        0,
                        0,
                        PlayerCommandButtons.None);
                // Appui maintenu jusqu'à la fin : le seuil d'effort d'une porte
                // lourde se compte en secondes, une fenêtre fixe le manquerait.
                case M1AutomatedPlayerProfile.InteractAfter120:
                    return InteractDuring(simulationTick, 120u, uint.MaxValue);
                case M1AutomatedPlayerProfile.InteractAfter180:
                    return InteractDuring(simulationTick, 180u, uint.MaxValue);
                case M1AutomatedPlayerProfile.PushLeft:
                    return ApproachAndPush(simulationTick, -127, FollowYawCentidegrees);
                case M1AutomatedPlayerProfile.PushRight:
                    return ApproachAndPush(simulationTick, 127, -FollowYawCentidegrees);
                case M1AutomatedPlayerProfile.PressLeft:
                    return ApproachAndPress(simulationTick, -127);
                case M1AutomatedPlayerProfile.PressRight:
                    return ApproachAndPress(simulationTick, 127);
                case M1AutomatedPlayerProfile.SandboxTrophyRun:
                    return RunSandboxTrophyRoute(simulationTick);
                case M1AutomatedPlayerProfile.SandboxRockTarget:
                    return MoveNorthAfterRoundStart(simulationTick);
                case M1AutomatedPlayerProfile.SandboxRockThrower:
                    return RunSandboxRockThrow(simulationTick);
                case M1AutomatedPlayerProfile.SandboxPuncher:
                    return RunSandboxPunches(simulationTick);
                default:
                    return new PlayerCommand(
                        simulationTick, 0, 0, 0, 0, PlayerCommandButtons.None);
            }
        }

        public static bool TryParseArguments(
            IReadOnlyList<string> arguments,
            out M1AutomatedCommandSource source,
            out string error)
        {
            source = default;
            error = string.Empty;
            if (arguments == null)
            {
                error = "arguments_null";
                return false;
            }

            string value = null;
            for (var index = 0; index < arguments.Count; index++)
            {
                var argument = arguments[index] ?? string.Empty;
                var prefix = ArgumentName + "=";
                if (argument.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                {
                    if (value != null)
                    {
                        error = "profile_duplicate";
                        return false;
                    }
                    value = argument.Substring(prefix.Length);
                    continue;
                }
                if (!string.Equals(argument, ArgumentName, StringComparison.OrdinalIgnoreCase))
                    continue;
                if (value != null || index + 1 >= arguments.Count)
                {
                    error = value != null ? "profile_duplicate" : "profile_value_missing";
                    return false;
                }
                value = arguments[++index];
            }

            if (value == null)
                return true;

            M1AutomatedPlayerProfile profile;
            switch (value.Trim().ToLowerInvariant())
            {
                case "none":
                    profile = M1AutomatedPlayerProfile.None;
                    break;
                case "clear-sweep":
                    profile = M1AutomatedPlayerProfile.ClearSweep;
                    break;
                case "interact-120":
                    profile = M1AutomatedPlayerProfile.InteractAfter120;
                    break;
                case "interact-180":
                    profile = M1AutomatedPlayerProfile.InteractAfter180;
                    break;
                case "push-left":
                    profile = M1AutomatedPlayerProfile.PushLeft;
                    break;
                case "press-left":
                    profile = M1AutomatedPlayerProfile.PressLeft;
                    break;
                case "press-right":
                    profile = M1AutomatedPlayerProfile.PressRight;
                    break;
                case "push-right":
                    profile = M1AutomatedPlayerProfile.PushRight;
                    break;
                case "sandbox-trophy-run":
                    profile = M1AutomatedPlayerProfile.SandboxTrophyRun;
                    break;
                case "sandbox-rock-target":
                    profile = M1AutomatedPlayerProfile.SandboxRockTarget;
                    break;
                case "sandbox-rock-thrower":
                    profile = M1AutomatedPlayerProfile.SandboxRockThrower;
                    break;
                case "sandbox-puncher":
                    profile = M1AutomatedPlayerProfile.SandboxPuncher;
                    break;
                default:
                    error = "profile_unknown";
                    return false;
            }

            source = new M1AutomatedCommandSource(profile);
            return true;
        }

        /// <summary>
        /// Vitesse de lacet, en centi-degrés par tick, qui suit un battant poussé à
        /// mi-longueur au réglage du banc. Elle fait tourner la direction de poussée
        /// avec la porte : sans elle, le pousseur reste face à sa position de départ
        /// et perd le contact au bout de quelques dizaines de degrés.
        ///
        /// Elle se déduit des réglages du director et doit être recalculée dès que
        /// l'un d'eux bouge : levier à mi-longueur
        /// <c>minimumLeveragePermille + (1000 - minimumLeveragePermille) / 2</c>,
        /// puis vitesse <c>levier × maximumAngularSpeed / 1000</c>, convertie en
        /// centi-degrés. Au réglage courant (400 mdeg/tick, levier plancher 400) :
        /// 700 pour mille, soit 280 mdeg/tick, donc 28. Trop haute, le pousseur
        /// dépasse la porte, bascule sur l'autre face et se met à la contre-pousser.
        /// </summary>
        private const short FollowYawCentidegrees = 28;

        /// <summary>
        /// Amplitude latérale maintenue une fois au contact du battant. Le point de
        /// contact ne s'éloigne qu'à <c>rayon × vitesse angulaire</c>, soit environ
        /// 0,40 m/s à mi-longueur au réglage courant, alors que la marche vaut
        /// 4,2 m/s : marcher à pleine amplitude ne pousse pas davantage, la porte
        /// oppose sa collision, et tout l'excédent se convertit en glissement le
        /// long du battant. Le pousseur finit par passer le bout et contre-pousse
        /// sa propre porte — c'est ce qui bloquait le scénario occupancy à 56°.
        /// Comme <see cref="FollowYawCentidegrees"/>, cette valeur suit la vitesse
        /// du battant et doit être revue avec elle.
        ///
        /// La poussée ne dépend pas de la force appliquée : la règle ne mesure que
        /// la portée depuis la capsule et l'abscisse du contact. Il suffit donc de
        /// rester collé à un battant qui fuit à 0,40 m/s, et 24 laisse 0,79 m/s,
        /// soit le double de marge sans l'excédent qui faisait sortir le pousseur.
        /// Mesuré sur occupancy : 127 inverse à 56°, 55 à 74°.
        /// </summary>
        private const int PushStrafeMagnitude = 24;

        /// <summary>
        /// Marche latérale continue, lacet asservi et appui maintenu. Un pousseur
        /// immobile perd le contact dès que le battant s'écarte de lui, exactement
        /// comme une vraie porte : accompagner la course fait partie du geste, donc
        /// du scénario. Le sens est lié à la disposition des apparitions du graybox.
        /// </summary>
        /// <summary>
        /// Marche latérale continue à pleine amplitude et appui jamais relâché.
        /// Sert au face à face : les deux couples s'annulent, le battant reste
        /// figé, donc rien ne s'écarte et l'amplitude réduite de
        /// <see cref="ApproachAndPush"/> n'a pas lieu d'être. La pleine amplitude
        /// est même nécessaire ici : le rebond de contact écarte le pousseur à
        /// 1,42 m/s, il faut pouvoir revenir plus vite que ça pour reprendre
        /// l'appui.
        /// </summary>
        private static PlayerCommand ApproachAndPress(uint simulationTick, sbyte strafe)
        {
            const uint approachTicks = 90u;
            var pressing = !TickMath.IsOlder(simulationTick, approachTicks);
            return new PlayerCommand(
                simulationTick,
                strafe,
                0,
                0,
                0,
                pressing ? PlayerCommandButtons.InteractHeld : PlayerCommandButtons.None);
        }

        private static PlayerCommand ApproachAndPush(
            uint simulationTick,
            sbyte strafe,
            short yawPerTick)
        {
            const uint approachTicks = 90u;
            // Relâcher une fois le quart de tour acquis. Un pousseur qui maintient
            // indéfiniment finit par dépasser le bout du battant, se retrouver sur
            // l'autre face et contre-pousser sa propre porte : occupancy montait à
            // 96° puis redescendait à 83°. La fenêtre couvre le balayage d'un quart
            // de tour au réglage du banc — 90000 mdeg à 280 mdeg/tick font 322
            // ticks, portés à 520 pour absorber l'approche et les pertes de contact
            // — et doit être rallongée si le battant est encore ralenti.
            const uint releaseTicks = approachTicks + 520u;
            if (!TickMath.IsOlder(simulationTick, releaseTicks))
                return new PlayerCommand(
                    simulationTick, 0, 0, 0, 0, PlayerCommandButtons.None);

            var pushing = !TickMath.IsOlder(simulationTick, approachTicks);
            // Pleine amplitude pour rejoindre le battant en 90 ticks, amplitude
            // réduite ensuite : une fois au contact, le surplus de vitesse ne
            // pousse pas plus fort, il fait glisser le pousseur le long du battant
            // jusqu'à le contourner et le prendre à revers.
            var lateral = pushing
                ? (sbyte)(Math.Sign(strafe) * PushStrafeMagnitude)
                : strafe;
            return new PlayerCommand(
                simulationTick,
                lateral,
                0,
                pushing ? yawPerTick : (short)0,
                0,
                pushing ? PlayerCommandButtons.InteractHeld : PlayerCommandButtons.None);
        }

        private static PlayerCommand InteractDuring(
            uint simulationTick,
            uint startTick,
            uint durationTicks)
        {
            var elapsed = unchecked(simulationTick - startTick);
            var held = !TickMath.IsOlder(simulationTick, startTick) && elapsed < durationTicks;
            var buttons = held
                ? PlayerCommandButtons.InteractHeld
                : PlayerCommandButtons.None;
            return new PlayerCommand(simulationTick, 0, 0, 0, 0, buttons);
        }

        private static PlayerCommand RunSandboxTrophyRoute(uint simulationTick)
        {
            // La première manche passe en Playing après trois secondes. Attendre
            // 200 ticks évite que son reset canonique ne remette le trophée au sol
            // juste après le ramassage automatisé.
            if (simulationTick >= 200u && simulationTick < 325u)
            {
                return new PlayerCommand(
                    simulationTick, 0, 127, 0, 0, PlayerCommandButtons.None);
            }
            if (simulationTick == 330u)
            {
                return new PlayerCommand(
                    simulationTick,
                    0,
                    0,
                    0,
                    0,
                    PlayerCommandButtons.InteractHeld |
                    PlayerCommandButtons.InteractPressed);
            }
            if (simulationTick >= 350u && simulationTick < 650u)
            {
                // Depuis le trophée (-1,375 ; +6,875) vers le dépôt
                // (+1,375 ; -6,875). Le premier tick fait demi-tour ; avec un yaw
                // de 180°, X local négatif devient X monde positif et Y local
                // positif devient Z monde négatif.
                return new PlayerCommand(
                    simulationTick,
                    -25,
                    125,
                    simulationTick == 350u ? (short)18000 : (short)0,
                    0,
                    PlayerCommandButtons.None);
            }
            return new PlayerCommand(
                simulationTick, 0, 0, 0, 0, PlayerCommandButtons.None);
        }

        private static PlayerCommand MoveNorthAfterRoundStart(uint simulationTick)
        {
            var move = simulationTick >= 200u && simulationTick < 270u
                ? (sbyte)127
                : (sbyte)0;
            return new PlayerCommand(
                simulationTick, 0, move, 0, 0, PlayerCommandButtons.None);
        }

        private static PlayerCommand RunSandboxRockThrow(uint simulationTick)
        {
            if (simulationTick >= 200u && simulationTick < 270u)
            {
                return new PlayerCommand(
                    simulationTick, 0, 127, 0, 0, PlayerCommandButtons.None);
            }
            if (simulationTick >= 280u && simulationTick < 370u)
            {
                // Du spawn droit déplacé au nord vers le caillou (6,875 ; 1,375).
                return new PlayerCommand(
                    simulationTick, 120, -41, 0, 0, PlayerCommandButtons.None);
            }
            if (simulationTick == 375u)
            {
                return new PlayerCommand(
                    simulationTick,
                    0,
                    0,
                    0,
                    0,
                    PlayerCommandButtons.InteractHeld |
                    PlayerCommandButtons.InteractPressed);
            }
            if (simulationTick == 385u)
            {
                return new PlayerCommand(
                    simulationTick, 0, 0, -7720, 0, PlayerCommandButtons.None);
            }
            if (simulationTick == 390u)
            {
                return new PlayerCommand(
                    simulationTick,
                    0,
                    0,
                    0,
                    0,
                    PlayerCommandButtons.PunchPressed);
            }
            return new PlayerCommand(
                simulationTick, 0, 0, 0, 0, PlayerCommandButtons.None);
        }

        private static PlayerCommand RunSandboxPunches(uint simulationTick)
        {
            if (simulationTick >= 200u && simulationTick < 270u)
            {
                return new PlayerCommand(
                    simulationTick, 0, 127, 0, 0, PlayerCommandButtons.None);
            }
            if (simulationTick >= 280u && simulationTick < 300u)
            {
                return new PlayerCommand(
                    simulationTick, -127, 0, 0, 0, PlayerCommandButtons.None);
            }
            if (simulationTick == 310u)
            {
                return new PlayerCommand(
                    simulationTick, 0, 0, -9000, 0, PlayerCommandButtons.None);
            }
            // Répéter brièvement chaque front rend la sonde robuste à la perte
            // d'un replicate sans multiplier les actions : les fenêtres restent
            // espacées de 50 ticks, au-delà du cooldown serveur de 48 ticks.
            if (IsInWindow(simulationTick, 320u, 3u) ||
                IsInWindow(simulationTick, 370u, 3u) ||
                IsInWindow(simulationTick, 420u, 3u) ||
                IsInWindow(simulationTick, 470u, 3u))
            {
                return new PlayerCommand(
                    simulationTick,
                    0,
                    0,
                    0,
                    0,
                    PlayerCommandButtons.PunchPressed);
            }
            if (simulationTick > 322u && simulationTick < 470u)
            {
                // Le knockback éloigne la cible d'environ un mètre à chaque
                // impact. Une entrée à 40/127 suit ce recul sur les 50 ticks du
                // cooldown sans dépasser la cible, contrairement à la marche à
                // pleine amplitude qui rendait la sonde dépendante des collisions.
                return new PlayerCommand(
                    simulationTick, 0, 40, 0, 0, PlayerCommandButtons.None);
            }
            return new PlayerCommand(
                simulationTick, 0, 0, 0, 0, PlayerCommandButtons.None);
        }

        private static bool IsInWindow(uint tick, uint start, uint duration)
        {
            var elapsed = unchecked(tick - start);
            return !TickMath.IsOlder(tick, start) && elapsed < duration;
        }
    }
}
