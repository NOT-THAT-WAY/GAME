using System;
using System.Collections.Generic;
using UnityEngine.InputSystem;

namespace NotThatWay.Game.Input
{
    public static class GameControlsContract
    {
        public const string PlayerMap = "Player";
        public const string UiMap = "UI";
        public const string KeyboardMouseScheme = "KeyboardMouse";
        public const string GamepadScheme = "Gamepad";

        public const string Move = "Move";
        public const string LookPointer = "LookPointer";
        public const string LookStick = "LookStick";
        public const string Sprint = "Sprint";
        public const string Interact = "Interact";
        public const string Punch = "Punch";
        public const string Drop = "Drop";
        public const string SelectSlot1 = "SelectSlot1";
        public const string SelectSlot2 = "SelectSlot2";
        public const string SelectSlot3 = "SelectSlot3";
        public const string CycleSlot = "CycleSlot";
        public const string Jump = "Jump";
        public const string Pause = "Pause";
        public const string ToggleView = "ToggleView";

        // Le zoom molette suit exactement le schéma de Look : un delta déjà
        // intégré côté souris (PassThrough, comme LookPointer) et un état continu
        // côté manette qu'il faut multiplier par dt pour rester indépendant du
        // framerate (Value, comme LookStick). Purement cosmétique et local
        // (ADR 0004) : jamais dans PlayerCommand, voir PlayerInputSource.
        public const string Zoom = "Zoom";
        public const string ZoomStick = "ZoomStick";

        private static readonly ActionRequirement[] Requirements =
        {
            new(PlayerMap, Move, InputActionType.Value, "Vector2", true, true),
            new(PlayerMap, LookPointer, InputActionType.PassThrough, "Vector2", true, false),
            new(PlayerMap, LookStick, InputActionType.Value, "Vector2", false, true),
            new(PlayerMap, Sprint, InputActionType.Button, "Button", true, true),
            new(PlayerMap, Interact, InputActionType.Button, "Button", true, true),
            new(PlayerMap, Punch, InputActionType.Button, "Button", true, true),
            new(PlayerMap, Drop, InputActionType.Button, "Button", true, true),
            new(PlayerMap, SelectSlot1, InputActionType.Button, "Button", true, false),
            new(PlayerMap, SelectSlot2, InputActionType.Button, "Button", true, false),
            new(PlayerMap, SelectSlot3, InputActionType.Button, "Button", true, false),
            new(PlayerMap, CycleSlot, InputActionType.Button, "Button", true, true),
            new(PlayerMap, Jump, InputActionType.Button, "Button", true, true),
            new(PlayerMap, Pause, InputActionType.Button, "Button", true, true),
            new(PlayerMap, ToggleView, InputActionType.Button, "Button", true, true),
            new(PlayerMap, Zoom, InputActionType.PassThrough, "Axis", true, false),
            new(PlayerMap, ZoomStick, InputActionType.Value, "Axis", false, true),
            new(UiMap, "Navigate", InputActionType.PassThrough, "Vector2", true, true),
            new(UiMap, "Submit", InputActionType.Button, "Button", true, true),
            new(UiMap, "Cancel", InputActionType.Button, "Button", true, true),
            new(UiMap, "Point", InputActionType.PassThrough, "Vector2", true, false),
            new(UiMap, "Click", InputActionType.PassThrough, "Button", true, false),
            new(UiMap, "Scroll", InputActionType.PassThrough, "Vector2", true, false)
        };

        public static bool TryValidate(InputActionAsset asset, out string error)
        {
            if (asset == null)
            {
                error = "input_asset_missing";
                return false;
            }
            if (!HasScheme(asset, KeyboardMouseScheme, "<Keyboard>", "<Mouse>"))
            {
                error = "keyboard_mouse_scheme_invalid";
                return false;
            }
            if (!HasScheme(asset, GamepadScheme, "<Gamepad>"))
            {
                error = "gamepad_scheme_invalid";
                return false;
            }

            var identifiers = new HashSet<Guid>();
            foreach (var map in asset.actionMaps)
            {
                if (!TryAddIdentifier(identifiers, map.id))
                {
                    error = $"map_id_invalid_or_duplicate:{map.name}";
                    return false;
                }
                foreach (var action in map.actions)
                {
                    if (!TryAddIdentifier(identifiers, action.id))
                    {
                        error = $"action_id_invalid_or_duplicate:{map.name}/{action.name}";
                        return false;
                    }
                }
                foreach (var binding in map.bindings)
                {
                    if (!TryAddIdentifier(identifiers, binding.id))
                    {
                        error = $"binding_id_invalid_or_duplicate:{map.name}/{binding.action}";
                        return false;
                    }
                    if (string.IsNullOrWhiteSpace(binding.path))
                    {
                        error = $"binding_path_missing:{map.name}/{binding.action}";
                        return false;
                    }
                }
            }

            foreach (var requirement in Requirements)
            {
                var map = asset.FindActionMap(requirement.MapName, false);
                var action = map?.FindAction(requirement.ActionName, false);
                if (action == null)
                {
                    error = $"action_missing:{requirement.MapName}/{requirement.ActionName}";
                    return false;
                }
                if (action.type != requirement.Type ||
                    !string.Equals(
                        action.expectedControlType,
                        requirement.ExpectedControlType,
                        StringComparison.Ordinal))
                {
                    error = $"action_contract_invalid:{requirement.MapName}/{requirement.ActionName}";
                    return false;
                }
                if (requirement.KeyboardMouse && !HasBindingGroup(action, KeyboardMouseScheme))
                {
                    error = $"keyboard_mouse_binding_missing:{requirement.MapName}/{requirement.ActionName}";
                    return false;
                }
                if (requirement.Gamepad && !HasBindingGroup(action, GamepadScheme))
                {
                    error = $"gamepad_binding_missing:{requirement.MapName}/{requirement.ActionName}";
                    return false;
                }
            }

            error = string.Empty;
            return true;
        }

        private static bool HasScheme(
            InputActionAsset asset,
            string name,
            params string[] requiredDevicePaths)
        {
            var index = asset.FindControlSchemeIndex(name);
            if (index < 0)
                return false;

            var scheme = asset.controlSchemes[index];
            foreach (var requiredPath in requiredDevicePaths)
            {
                var found = false;
                foreach (var device in scheme.deviceRequirements)
                {
                    if (string.Equals(device.controlPath, requiredPath, StringComparison.Ordinal))
                    {
                        found = true;
                        break;
                    }
                }
                if (!found)
                    return false;
            }
            return true;
        }

        private static bool HasBindingGroup(InputAction action, string group)
        {
            foreach (var binding in action.bindings)
            {
                var groups = binding.groups;
                if (string.IsNullOrEmpty(groups))
                    continue;
                foreach (var candidate in groups.Split(';'))
                {
                    if (string.Equals(candidate, group, StringComparison.Ordinal))
                        return true;
                }
            }
            return false;
        }

        private static bool TryAddIdentifier(HashSet<Guid> identifiers, Guid identifier) =>
            identifier != Guid.Empty && identifiers.Add(identifier);

        private readonly struct ActionRequirement
        {
            public ActionRequirement(
                string mapName,
                string actionName,
                InputActionType type,
                string expectedControlType,
                bool keyboardMouse,
                bool gamepad)
            {
                MapName = mapName;
                ActionName = actionName;
                Type = type;
                ExpectedControlType = expectedControlType;
                KeyboardMouse = keyboardMouse;
                Gamepad = gamepad;
            }

            public string MapName { get; }
            public string ActionName { get; }
            public InputActionType Type { get; }
            public string ExpectedControlType { get; }
            public bool KeyboardMouse { get; }
            public bool Gamepad { get; }
        }
    }
}
