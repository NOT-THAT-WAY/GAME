using NotThatWay.Game.Input;
using NotThatWay.Game.PlayerSimulation;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.InputSystem;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class GameControlsInputTests : InputTestFixture
    {
        private const string AssetPath = "Assets/_Project/Input/GameControls.inputactions";

        [Test]
        public void Asset_SatisfiesCanonicalMapsActionsSchemesAndBindings()
        {
            var asset = LoadAsset();

            Assert.That(GameControlsContract.TryValidate(asset, out var error), Is.True, error);
            Assert.That(asset.actionMaps, Has.Count.EqualTo(2));
            Assert.That(asset.controlSchemes, Has.Count.EqualTo(2));
            foreach (var map in asset.actionMaps)
            {
                foreach (var action in map.actions)
                    Assert.That(action.processors, Does.Not.Contain("stickDeadzone"));
                foreach (var binding in map.bindings)
                    Assert.That(binding.processors, Does.Not.Contain("stickDeadzone"));
            }
        }

        [Test]
        public void KeyboardBindings_KeepDropASeparateFromCanonicalZqsdMovement()
        {
            var player = LoadAsset().FindActionMap(GameControlsContract.PlayerMap, true);
            var move = player.FindAction(GameControlsContract.Move, true);
            var drop = player.FindAction(GameControlsContract.Drop, true);
            var interact = player.FindAction(GameControlsContract.Interact, true);
            var primary = player.FindAction(GameControlsContract.Punch, true);

            // Les touches sont liées PAR CARACTÈRE, pas par position physique.
            // `<Keyboard>/z` désigne la position de Z sur un clavier US, c'est-à-dire
            // la touche marquée W en AZERTY : le déplacement tombait alors sur WASD
            // et « gauche » atterrissait sur A, ce que le contrat interdit.
            // `<Keyboard>/#(z)` désigne la touche qui produit le caractère z dans la
            // disposition courante, donc le vrai Z d'un AZERTY.
            Assert.That(HasPath(move, "<Keyboard>/#(z)"), Is.True);
            Assert.That(HasPath(move, "<Keyboard>/#(q)"), Is.True);
            Assert.That(HasPath(move, "<Keyboard>/#(s)"), Is.True);
            Assert.That(HasPath(move, "<Keyboard>/#(d)"), Is.True);
            Assert.That(HasPath(move, "<Keyboard>/#(a)"), Is.False);
            Assert.That(HasPath(drop, "<Keyboard>/#(a)"), Is.True);

            // La liaison par position physique ne doit plus exister : c'est elle qui
            // faisait récupérer A par un binding de mouvement en AZERTY.
            Assert.That(HasPath(move, "<Keyboard>/z"), Is.False);
            Assert.That(HasPath(move, "<Keyboard>/q"), Is.False);
            Assert.That(HasPath(move, "<Keyboard>/a"), Is.False);
            Assert.That(HasPath(drop, "<Keyboard>/a"), Is.False);

            // Les flèches restent une alternative indépendante de la disposition.
            Assert.That(HasPath(move, "<Keyboard>/upArrow"), Is.True);
            Assert.That(HasPath(move, "<Keyboard>/leftArrow"), Is.True);
            Assert.That(HasPath(interact, "<Keyboard>/e"), Is.True);
            Assert.That(HasPath(interact, "<Mouse>/leftButton"), Is.False);
            Assert.That(HasPath(primary, "<Mouse>/leftButton"), Is.True);
            Assert.That(HasPath(primary, "<Keyboard>/f"), Is.True);
        }

        [Test]
        public void KeyboardMouse_ProducesHeldEdgesAndPointerDelta()
        {
            var keyboard = InputSystem.AddDevice<Keyboard>();
            var mouse = InputSystem.AddDevice<Mouse>();
            var source = CreateSource(keyboard, mouse);
            try
            {
                Press(keyboard.zKey);
                Press(keyboard.leftShiftKey);
                Press(keyboard.spaceKey, queueEventOnly: true);
                Press(mouse.leftButton, queueEventOnly: true);
                Press(mouse.rightButton, queueEventOnly: true);
                Press(keyboard.aKey, queueEventOnly: true);
                Press(keyboard.leftCtrlKey, queueEventOnly: true);
                Set(mouse.delta, new Vector2(10f, -5f), queueEventOnly: true);
                InputSystem.Update();

                Release(keyboard.spaceKey, queueEventOnly: true);
                Release(mouse.leftButton, queueEventOnly: true);
                Release(keyboard.aKey, queueEventOnly: true);
                Release(keyboard.leftCtrlKey, queueEventOnly: true);
                InputSystem.Update();

                var command = source.ConsumeCommand(10u, 1f / 60f);
                Assert.That(command.MoveX, Is.Zero);
                Assert.That(command.MoveY, Is.EqualTo(127));
                Assert.That(command.LookYaw, Is.EqualTo(120));
                Assert.That(command.LookPitch, Is.EqualTo(-60));
                Assert.That(command.Has(PlayerCommandButtons.SprintHeld), Is.True);
                Assert.That(command.Has(PlayerCommandButtons.JumpPressed), Is.True);
                Assert.That(command.Has(PlayerCommandButtons.PunchPressed), Is.True);
                Assert.That(command.Has(PlayerCommandButtons.DropPressed), Is.True);
                Assert.That(command.Has(PlayerCommandButtons.DivePressed), Is.True);
                Assert.That(command.Has(PlayerCommandButtons.SlingshotPressed), Is.True);
                Assert.That(command.Has(PlayerCommandButtons.SlingshotHeld), Is.True,
                    "Le clic droit est encore tenu au moment de consommer la commande.");
                Assert.That(command.Has(PlayerCommandButtons.PunchHeld), Is.False,
                    "Le clic gauche a été relâché avant la consommation.");
                var next = source.ConsumeCommand(11u, 1f / 60f);
                Assert.That(next.Has(PlayerCommandButtons.PunchPressed), Is.False);
                Assert.That(next.Has(PlayerCommandButtons.DivePressed), Is.False);
                Assert.That(next.Has(PlayerCommandButtons.SlingshotPressed), Is.False);
                Assert.That(next.Has(PlayerCommandButtons.SlingshotHeld), Is.True);
            }
            finally
            {
                Object.DestroyImmediate(source.gameObject);
            }
        }

        [Test]
        public void Gamepad_UsesStickAsRateOncePerTick()
        {
            var gamepad = InputSystem.AddDevice<Gamepad>();
            var source = CreateSource(gamepad);
            try
            {
                Set(gamepad.leftStick, Vector2.up);
                Set(gamepad.rightStick, Vector2.right);
                Press(gamepad.leftStickButton);
                Press(gamepad.buttonSouth);
                Press(gamepad.rightTrigger);

                // Les mises à jour Input ont été multiples, mais le taux stick est
                // intégré exactement une fois à la consommation du tick.
                var command = source.ConsumeCommand(20u, 1f / 60f);

                Assert.That(command.MoveY, Is.EqualTo(127));
                Assert.That(command.LookYaw, Is.EqualTo(300));
                Assert.That(command.LookPitch, Is.Zero);
                Assert.That(command.Has(PlayerCommandButtons.SprintHeld), Is.True);
                Assert.That(command.Has(PlayerCommandButtons.JumpPressed), Is.True);
                Assert.That(command.Has(PlayerCommandButtons.PunchPressed), Is.True);
            }
            finally
            {
                Object.DestroyImmediate(source.gameObject);
            }
        }

        [Test]
        public void TwoSources_CanBeRestrictedToIndependentDevices()
        {
            var keyboard = InputSystem.AddDevice<Keyboard>();
            var mouse = InputSystem.AddDevice<Mouse>();
            var gamepad = InputSystem.AddDevice<Gamepad>();
            var keyboardSource = CreateSource(keyboard, mouse);
            var gamepadSource = CreateSource(gamepad);
            try
            {
                Press(keyboard.dKey, queueEventOnly: true);
                Set(gamepad.leftStick, Vector2.left, queueEventOnly: true);
                InputSystem.Update();

                var keyboardCommand = keyboardSource.ConsumeCommand(1u, 1f / 60f);
                var gamepadCommand = gamepadSource.ConsumeCommand(1u, 1f / 60f);
                Assert.That(keyboardCommand.MoveX, Is.EqualTo(127));
                Assert.That(gamepadCommand.MoveX, Is.EqualTo(-127));
            }
            finally
            {
                Object.DestroyImmediate(keyboardSource.gameObject);
                Object.DestroyImmediate(gamepadSource.gameObject);
            }
        }

        [Test]
        public void ExplicitReset_ClearsBufferedEdgesAndHeldState()
        {
            var keyboard = InputSystem.AddDevice<Keyboard>();
            var mouse = InputSystem.AddDevice<Mouse>();
            var source = CreateSource(keyboard, mouse);
            try
            {
                Press(keyboard.spaceKey);
                Release(keyboard.spaceKey);
                source.ResetBufferedInput();

                var command = source.ConsumeCommand(1u, 1f / 60f);
                Assert.That(command.Has(PlayerCommandButtons.JumpPressed), Is.False);
                Assert.That(command.MoveX, Is.Zero);
                Assert.That(command.MoveY, Is.Zero);
            }
            finally
            {
                Object.DestroyImmediate(source.gameObject);
            }
        }

        [Test]
        public void DeviceRestrictionChange_ClearsBufferedEdges()
        {
            var keyboard = InputSystem.AddDevice<Keyboard>();
            var mouse = InputSystem.AddDevice<Mouse>();
            var source = CreateSource(keyboard, mouse);
            try
            {
                Press(keyboard.spaceKey);
                source.RestrictToDevices(keyboard, mouse);

                Assert.That(source.ConsumeCommand(1u, 1f / 60f)
                    .Has(PlayerCommandButtons.JumpPressed), Is.False);
            }
            finally
            {
                Object.DestroyImmediate(source.gameObject);
            }
        }

        [Test]
        public void Pause_IsReportedLocallyButNeverEntersTheNetworkCommand()
        {
            var keyboard = InputSystem.AddDevice<Keyboard>();
            var mouse = InputSystem.AddDevice<Mouse>();
            var source = CreateSource(keyboard, mouse);
            try
            {
                Press(keyboard.escapeKey);

                Assert.That(source.PausePressedThisFrame, Is.True);
                Assert.That(source.ConsumeCommand(1u, 1f / 60f).Buttons,
                    Is.EqualTo(PlayerCommandButtons.None));
            }
            finally
            {
                Object.DestroyImmediate(source.gameObject);
            }
        }

        private static InputActionAsset LoadAsset()
        {
            var asset = AssetDatabase.LoadAssetAtPath<InputActionAsset>(AssetPath);
            Assert.That(asset, Is.Not.Null, $"Asset Input Actions absent: {AssetPath}");
            return asset;
        }

        private static PlayerInputSource CreateSource(params InputDevice[] devices)
        {
            var gameObject = new GameObject("Input source under test");
            var source = gameObject.AddComponent<PlayerInputSource>();
            source.RestrictToDevices(devices);
            source.Configure(LoadAsset());
            Assert.That(source.IsReady, Is.True);
            return source;
        }

        private static bool HasPath(InputAction action, string path)
        {
            foreach (var binding in action.bindings)
            {
                if (binding.path == path)
                    return true;
            }
            return false;
        }
    }
}
