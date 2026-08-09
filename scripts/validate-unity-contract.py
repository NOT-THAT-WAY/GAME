#!/usr/bin/env python3
"""Validate the cross-platform Unity contract without opening the Editor."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ERRORS: list[str] = []


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def parse_toolchain() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in read("config/toolchain.env").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        require(bool(separator and key and value), f"Invalid toolchain line: {raw_line}")
        if separator:
            values[key] = value
    return values


toolchain = parse_toolchain()
required_contract = {
    "PLAYER_TARGET": "Windows-x86_64-IL2CPP",
    "DEVELOPMENT_PLATFORMS": "macOS-Apple-Silicon,Windows-x86_64",
    "DEFAULT_NETWORK_PORT": "7770",
    "WWISE_ENABLED": "0",
    "STEAM_TRANSPORT_ENABLED": "0",
    "UNITY_CI_BUILDS_ENABLED": "0",
}
for key, expected in required_contract.items():
    require(toolchain.get(key) == expected, f"{key} must be {expected!r} during M0")

manifest = json.loads(read("Packages/manifest.json"))
lockfile = json.loads(read("Packages/packages-lock.json"))
manifest_dependencies = manifest.get("dependencies", {})
locked_dependencies = lockfile.get("dependencies", {})

expected_packages = {
    "com.firstgeargames.fishnet": (
        "https://github.com/FirstGearGames/FishNet.git?path=/Assets/FishNet#"
        + toolchain["FISHNET_VERSION"]
    ),
    "com.unity.inputsystem": toolchain["INPUT_SYSTEM_VERSION"],
    "com.unity.multiplayer.playmode": toolchain["MULTIPLAYER_PLAYMODE_VERSION"],
    "com.unity.multiplayer.tools": toolchain["MULTIPLAYER_TOOLS_VERSION"],
    "com.unity.nuget.newtonsoft-json": toolchain["NEWTONSOFT_JSON_VERSION"],
    "com.unity.render-pipelines.universal": toolchain["URP_VERSION"],
}
for package, expected_version in expected_packages.items():
    require(
        manifest_dependencies.get(package) == expected_version,
        f"manifest version mismatch for {package}: expected {expected_version}",
    )
    locked = locked_dependencies.get(package, {})
    require(locked.get("version") == expected_version, f"lockfile mismatch for {package}")
    require(locked.get("depth") == 0, f"{package} must remain a direct dependency")

fishnet_hash = locked_dependencies.get("com.firstgeargames.fishnet", {}).get("hash", "")
require(bool(re.fullmatch(r"[0-9a-f]{40}", fishnet_hash)), "FishNet lock hash is missing")

project_version = read("ProjectSettings/ProjectVersion.txt")
require(
    f"m_EditorVersion: {toolchain['UNITY_VERSION']}" in project_version,
    "ProjectVersion.txt does not match UNITY_VERSION",
)
require(
    f"({toolchain['UNITY_CHANGESET']})" in project_version,
    "ProjectVersion.txt does not match UNITY_CHANGESET",
)

project_settings = read("ProjectSettings/ProjectSettings.asset")
require(f"bundleVersion: {toolchain['BUNDLE_VERSION']}" in project_settings, "bundleVersion mismatch")
require("Standalone: com.notthatway.game" in project_settings, "Standalone identifier mismatch")
require("useDeterministicCompilation: 1" in project_settings, "deterministic compilation must stay enabled")
require("allowUnsafeCode: 0" in project_settings, "unsafe code must stay disabled by default")

team_settings = read("Assets/_Project/Editor/TeamProjectSettings.cs")
require(
    f'ExpectedUnityVersion = "{toolchain["UNITY_VERSION"]}"' in team_settings,
    "TeamProjectSettings Unity version mismatch",
)

game_version = read("Assets/_Project/Runtime/GameVersion.cs")
require(
    f'Current = "{toolchain["GAME_VERSION"]}"' in game_version,
    "GameVersion.Current mismatch",
)

connection_test = read("Assets/_Project/Runtime/ConnectionSmokeTest.cs")
require(
    f"DefaultPort = {toolchain['DEFAULT_NETWORK_PORT']}" in connection_test,
    "Connection smoke-test port mismatch",
)

build_code = read("Assets/_Project/Editor/ConnectionTestBuild.cs")
require("BuildTarget.StandaloneOSX" in build_code, "macOS development build target missing")
require("BuildTarget.StandaloneWindows64" in build_code, "Windows x86_64 build target missing")
require("ScriptingImplementation.IL2CPP" in build_code, "Windows IL2CPP build contract missing")
require("BuildOptions.Development" in build_code, "connection proof must remain a Development build")

editor_build_settings = read("ProjectSettings/EditorBuildSettings.asset")
require("Assets/Scenes/SampleScene.unity" in editor_build_settings, "bootstrap scene missing")

if toolchain["WWISE_ENABLED"] == "0":
    require(
        not any(name.lower().startswith("com.audiokinetic") for name in manifest_dependencies),
        "Wwise package added while WWISE_ENABLED=0",
    )
if toolchain["STEAM_TRANSPORT_ENABLED"] == "0":
    require(
        not any("steam" in name.lower() for name in manifest_dependencies),
        "Steam package added while STEAM_TRANSPORT_ENABLED=0",
    )
if toolchain["UNITY_CI_BUILDS_ENABLED"] == "0":
    require(
        not (ROOT / ".github/workflows/unity-build.yml").exists(),
        "Unity build workflow added while UNITY_CI_BUILDS_ENABLED=0",
    )

if ERRORS:
    for error in ERRORS:
        print(f"Unity contract error: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Unity contract checks passed.")
