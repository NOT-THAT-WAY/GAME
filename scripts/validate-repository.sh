#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd -- "$REPO_ROOT"

EXPECTED_UNITY="$(sed -n 's/^UNITY_VERSION=//p' config/toolchain.env)"
PROJECT_UNITY="$(sed -n 's/^m_EditorVersion: //p' ProjectSettings/ProjectVersion.txt)"

while IFS= read -r BASH_SCRIPT; do
  bash -n "$BASH_SCRIPT"
done < <(git ls-files '*.sh' '.githooks/pre-commit' '.githooks/pre-push')

if [[ "$EXPECTED_UNITY" != "$PROJECT_UNITY" ]]; then
  printf 'Unity mismatch: toolchain=%s project=%s\n' "$EXPECTED_UNITY" "$PROJECT_UNITY" >&2
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  python3 -m json.tool Packages/manifest.json >/dev/null
elif command -v jq >/dev/null 2>&1; then
  jq empty Packages/manifest.json
else
  printf 'python3 ou jq est requis pour valider le manifest.\n' >&2
  exit 1
fi

grep -Fq 'FishNet.git?path=/Assets/FishNet#4.7.2' Packages/manifest.json
grep -Fq '"com.unity.render-pipelines.universal": "17.3.0"' Packages/manifest.json
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

LFS_ATTRIBUTE="$(git check-attr filter -- Assets/_Project/Test.png)"
[[ "$LFS_ATTRIBUTE" == *": lfs" ]]

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
git diff --check -- "${CHECKED_PATHS[@]}"
git diff --cached --check -- "${CHECKED_PATHS[@]}"
printf 'Repository checks passed.\n'
