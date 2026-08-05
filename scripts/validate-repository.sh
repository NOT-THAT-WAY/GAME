#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd -- "$REPO_ROOT"

EXPECTED_UNITY="$(sed -n 's/^UNITY_VERSION=//p' config/toolchain.env)"
EXPECTED_CHANGESET="$(sed -n 's/^UNITY_CHANGESET=//p' config/toolchain.env)"
EXPECTED_INPUT_SYSTEM="$(sed -n 's/^INPUT_SYSTEM_VERSION=//p' config/toolchain.env)"
EXPECTED_MULTIPLAYER_PLAYMODE="$(sed -n 's/^MULTIPLAYER_PLAYMODE_VERSION=//p' config/toolchain.env)"
EXPECTED_MULTIPLAYER_TOOLS="$(sed -n 's/^MULTIPLAYER_TOOLS_VERSION=//p' config/toolchain.env)"
PROJECT_UNITY="$(sed -n 's/^m_EditorVersion: //p' ProjectSettings/ProjectVersion.txt)"
PROJECT_CHANGESET="$(sed -n 's/^m_EditorVersionWithRevision: .*(\([^)]*\)).*/\1/p' ProjectSettings/ProjectVersion.txt)"

[[ -f CLAUDE.md ]]
[[ -f docs/PROJECT_RULES.md ]]
[[ -f docs/CI_BUILDS.md ]]
[[ -f .claude/skills/setup-game/SKILL.md ]]
[[ -f .claude/skills/lan-test/SKILL.md ]]
[[ -f .claude/skills/git-task/SKILL.md ]]
[[ -f .claude/skills/remote-test/SKILL.md ]]
[[ -f .claude/skills/network-gameplay/SKILL.md ]]
[[ -f docs/adr/0004-authoritative-topology-and-ticks.md ]]
grep -Fq 'name: setup-game' .claude/skills/setup-game/SKILL.md
grep -Fq 'name: lan-test' .claude/skills/lan-test/SKILL.md
grep -Fq 'name: git-task' .claude/skills/git-task/SKILL.md
grep -Fq 'name: remote-test' .claude/skills/remote-test/SKILL.md
grep -Fq 'name: network-gameplay' .claude/skills/network-gameplay/SKILL.md
grep -Fq 'skill `network-gameplay`' CLAUDE.md

for NETWORK_RULE in \
  'Time.deltaTime' \
  'startTick' \
  'schemaVersion' \
  'Replicate`/`Reconcile' \
  'MeshCollider' \
  'ConnectionTarget' \
  '80 ms RTT / 2 % perte / 20 ms jitter'; do
  if ! grep -Fq "$NETWORK_RULE" .claude/skills/network-gameplay/SKILL.md || \
     ! grep -Fq "$NETWORK_RULE" docs/adr/0004-authoritative-topology-and-ticks.md; then
    printf 'Network gameplay guardrail missing from skill or ADR: %s\n' "$NETWORK_RULE" >&2
    exit 1
  fi
done
[[ -x scripts/tailscale-macos.sh ]]
[[ -x scripts/remote-test-macos.sh ]]
[[ -f scripts/tailscale-windows.ps1 ]]
[[ -f scripts/remote-test-windows.ps1 ]]
[[ -f docs/REMOTE_CONNECTION_TEST.md ]]
grep -Fq 'tailscale-app' scripts/setup-macos.sh
grep -Fq 'Tailscale.Tailscale' scripts/setup-windows.ps1
grep -Fq 'refs/heads/main' .githooks/pre-push
if grep -Fq 'GAME_ALLOW_MAIN_PUSH' .githooks/pre-push CLAUDE.md docs/WORKFLOW.md; then
  printf 'Le contournement explicite du push main ne doit pas être documenté ni activé.\n' >&2
  exit 1
fi

UNPINNED_ACTIONS="$(git grep -h -E '^[[:space:]]*uses:[[:space:]]+' -- .github/workflows | awk '$2 !~ /^\.\// && $2 !~ /@[0-9a-f]{40}$/ { print }')"
if [[ -n "$UNPINNED_ACTIONS" ]]; then
  printf 'GitHub Actions must use a full commit SHA:\n%s\n' "$UNPINNED_ACTIONS" >&2
  exit 1
fi

while IFS= read -r BASH_SCRIPT; do
  bash -n "$BASH_SCRIPT"
done < <(git ls-files '*.sh' '.githooks/pre-commit' '.githooks/pre-push')

if [[ "$EXPECTED_UNITY" != "$PROJECT_UNITY" ]]; then
  printf 'Unity mismatch: toolchain=%s project=%s\n' "$EXPECTED_UNITY" "$PROJECT_UNITY" >&2
  exit 1
fi
if [[ "$EXPECTED_CHANGESET" != "$PROJECT_CHANGESET" ]]; then
  printf 'Unity changeset mismatch: toolchain=%s project=%s\n' "$EXPECTED_CHANGESET" "$PROJECT_CHANGESET" >&2
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  python3 scripts/validate-unity-contract.py
elif command -v jq >/dev/null 2>&1; then
  jq empty Packages/manifest.json
  jq empty Packages/packages-lock.json
elif command -v powershell.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1; then
  for JSON_FILE in Packages/manifest.json Packages/packages-lock.json; do
    GAME_JSON_PATH="$(cygpath -w "$JSON_FILE")" powershell.exe -NoProfile -NonInteractive -Command \
      '$ErrorActionPreference = "Stop"; $null = Get-Content -Raw -LiteralPath $env:GAME_JSON_PATH | ConvertFrom-Json'
  done
else
  printf 'python3, jq ou PowerShell est requis pour valider les fichiers JSON.\n' >&2
  exit 1
fi

grep -Fq 'FishNet.git?path=/Assets/FishNet#4.7.2' Packages/manifest.json
grep -Fq '"com.unity.render-pipelines.universal": "17.3.0"' Packages/manifest.json
grep -Fq "\"com.unity.inputsystem\": \"$EXPECTED_INPUT_SYSTEM\"" Packages/manifest.json
grep -Fq "\"com.unity.multiplayer.playmode\": \"$EXPECTED_MULTIPLAYER_PLAYMODE\"" Packages/manifest.json
grep -Fq "\"com.unity.multiplayer.tools\": \"$EXPECTED_MULTIPLAYER_TOOLS\"" Packages/manifest.json
grep -Fq 'm_SerializationMode: 2' ProjectSettings/EditorSettings.asset
grep -Fq 'm_Mode: Visible Meta Files' ProjectSettings/VersionControlSettings.asset
grep -Fq 'companyName: NOT THAT WAY' ProjectSettings/ProjectSettings.asset
grep -Fq 'productName: GAME' ProjectSettings/ProjectSettings.asset
grep -Fq 'Standalone: com.notthatway.game' ProjectSettings/ProjectSettings.asset

[[ -f .dvc/config ]]
if git ls-files --error-unmatch .dvc/config.local >/dev/null 2>&1; then
  printf '.dvc/config.local contient la configuration locale et ne doit jamais être suivi.\n' >&2
  exit 1
fi

SENSITIVE_PATHS="$(git ls-files | awk '
  {
    path=tolower($0)
    if (path ~ /(^|\/)\.env($|\.)/ && path !~ /\.env\.example$/) print
    else if (path ~ /(^|\/)(id_rsa|id_ed25519)(\.pub)?$/) print
    else if (path ~ /\.(pem|p12|pfx|key)$/) print
    else if (path ~ /(^|\/)(credentials|secrets?)(\.|\/|$)/) print
    else if (path ~ /(^|\/)steam_appid\.txt$/) print
  }
')"
if [[ -n "$SENSITIVE_PATHS" ]]; then
  printf 'Sensitive-looking files must stay outside Git:\n%s\n' "$SENSITIVE_PATHS" >&2
  exit 1
fi

LFS_ATTRIBUTE="$(git check-attr filter -- Assets/_Project/Test.png)"
[[ "$LFS_ATTRIBUTE" == *": lfs" ]]

WWISE_LFS_ATTRIBUTE="$(git check-attr filter -- Assets/StreamingAssets/Audio/GeneratedSoundBanks/Test.bnk)"
[[ "$WWISE_LFS_ATTRIBUTE" == *": lfs" ]]

RAW_MASTERS="$(git ls-files | awk 'BEGIN{IGNORECASE=1} /\.(blend|blend[0-9]+|kra|psb|psd|als|logicx|rpp|sesx)$/ {print}')"
if [[ -n "$RAW_MASTERS" ]]; then
  printf 'Editable masters must be tracked through DVC, outside GitHub:\n%s\n' "$RAW_MASTERS" >&2
  exit 1
fi

INVALID_EXTERNAL="$(git ls-files ExternalAssets | awk '!/\.dvc$/ && !/(^|\/)\.gitignore$/ {print}')"
if [[ -n "$INVALID_EXTERNAL" ]]; then
  printf 'ExternalAssets may contain only DVC pointers and generated ignore files in Git:\n%s\n' "$INVALID_EXTERNAL" >&2
  exit 1
fi

MISSING_META=""
while IFS= read -r ASSET_PATH; do
  [[ "$ASSET_PATH" == *.meta ]] && continue
  [[ "$ASSET_PATH" == Assets/_GeneratedLocal/* ]] && continue
  if [[ ! -f "${ASSET_PATH}.meta" ]]; then
    MISSING_META="${MISSING_META}${ASSET_PATH}"$'\n'
  fi
done < <(git ls-files Assets)
if [[ -n "$MISSING_META" ]]; then
  printf 'Unity assets missing their .meta file:\n%s' "$MISSING_META" >&2
  exit 1
fi

ORPHAN_META=""
while IFS= read -r META_PATH; do
  SOURCE_PATH="${META_PATH%.meta}"
  if [[ ! -e "$SOURCE_PATH" ]]; then
    ORPHAN_META="${ORPHAN_META}${META_PATH}"$'\n'
  fi
done < <(git ls-files 'Assets/*.meta' 'Assets/**/*.meta')
if [[ -n "$ORPHAN_META" ]]; then
  printf 'Orphan Unity .meta files:\n%s' "$ORPHAN_META" >&2
  exit 1
fi

LARGE_NON_LFS=""
while IFS= read -r -d '' TRACKED_PATH; do
  [[ -f "$TRACKED_PATH" ]] || continue
  FILE_SIZE="$(wc -c < "$TRACKED_PATH" | tr -d ' ')"
  (( FILE_SIZE > 10485760 )) || continue
  FILE_ATTRIBUTE="$(git check-attr filter -- "$TRACKED_PATH")"
  if [[ "$FILE_ATTRIBUTE" != *": lfs" ]]; then
    LARGE_NON_LFS="${LARGE_NON_LFS}${TRACKED_PATH} (${FILE_SIZE} bytes)"$'\n'
  fi
done < <(git ls-files -z)
if [[ -n "$LARGE_NON_LFS" ]]; then
  printf 'Files above 10 MiB must use LFS or DVC:\n%s' "$LARGE_NON_LFS" >&2
  exit 1
fi

FORBIDDEN_TRACKED="$(git ls-files | awk 'BEGIN{IGNORECASE=1} /(^|\/)(Library|Temp|Obj|Logs|UserSettings|Build|Builds)(\/|$)/ {print}')"
if [[ -n "$FORBIDDEN_TRACKED" ]]; then
  printf 'Generated Unity paths are tracked:\n%s\n' "$FORBIDDEN_TRACKED" >&2
  exit 1
fi

CASE_COLLISIONS="$(git ls-files | awk '{print tolower($0)}' | sort | uniq -d)"
if [[ -n "$CASE_COLLISIONS" ]]; then
  printf 'Case-insensitive path collisions:\n%s\n' "$CASE_COLLISIONS" >&2
  exit 1
fi

# Unity's own YAML serializer emits trailing spaces for empty scalar values.
# Keep whitespace checks strict for human-authored files without rewriting
# serialized scenes/settings after every Editor import.
CHECKED_PATHS=('*.cs' '*.json' '*.md' '*.sh' '*.ps1' '*.yml' '*.yaml' '*.env' '*.dvc' '.gitignore' '.gitattributes' '.editorconfig' '.dvcignore' '.dvc/config')
CHECKED_PATHS+=('*.py')
git diff --check -- "${CHECKED_PATHS[@]}"
git diff --cached --check -- "${CHECKED_PATHS[@]}"
printf 'Repository checks passed.\n'
