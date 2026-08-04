#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TOOLCHAIN_FILE="$REPO_ROOT/config/toolchain.env"
UNITY_VERSION="$(sed -n 's/^UNITY_VERSION=//p' "$TOOLCHAIN_FILE")"
UNITY_CHANGESET="$(sed -n 's/^UNITY_CHANGESET=//p' "$TOOLCHAIN_FILE")"
UNITY_EDITOR="${GAME_UNITY_EDITOR:-/Applications/Unity/Hub/Editor/$UNITY_VERSION/Unity.app/Contents/MacOS/Unity}"
INSTALL_TOOLS=0
OPEN_UNITY=0
ASSET_REMOTE=""
ASSET_ENDPOINT=""
ASSET_PROFILE=""

find_smart_merge() {
  local unity_contents candidate
  unity_contents="$(cd -- "$(dirname -- "$UNITY_EDITOR")/.." && pwd)"

  for candidate in \
    "$unity_contents/Helpers/UnityYAMLMerge" \
    "$unity_contents/Tools/UnityYAMLMerge"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

usage() {
  printf 'Usage: %s [--install-tools] [--open-unity] [--all] [--asset-remote URL] [--asset-endpoint URL] [--asset-profile NAME]\n' "$0"
}

while (( $# > 0 )); do
  case "$1" in
    --install-tools) INSTALL_TOOLS=1 ;;
    --open-unity) OPEN_UNITY=1 ;;
    --all) INSTALL_TOOLS=1; OPEN_UNITY=1 ;;
    --asset-remote)
      (( $# >= 2 )) || { printf '%s\n' '--asset-remote attend une URL.' >&2; exit 2; }
      ASSET_REMOTE="$2"
      shift
      ;;
    --asset-endpoint)
      (( $# >= 2 )) || { printf '%s\n' '--asset-endpoint attend une URL.' >&2; exit 2; }
      ASSET_ENDPOINT="$2"
      shift
      ;;
    --asset-profile)
      (( $# >= 2 )) || { printf '%s\n' '--asset-profile attend un nom.' >&2; exit 2; }
      ASSET_PROFILE="$2"
      shift
      ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Argument inconnu: %s\n' "$1" >&2; usage; exit 2 ;;
  esac
  shift
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  printf 'Ce script doit être exécuté sur macOS.\n' >&2
  exit 1
fi

cd -- "$REPO_ROOT"

if (( INSTALL_TOOLS == 1 )); then
  if ! command -v brew >/dev/null 2>&1; then
    printf 'Homebrew est requis pour --install-tools. Installez-le depuis https://brew.sh puis relancez.\n' >&2
    exit 1
  fi

  brew install git git-lfs gh dvc
  if ! brew list --cask unity-hub >/dev/null 2>&1; then
    brew install --cask unity-hub
  fi
fi

if ! command -v git >/dev/null 2>&1; then
  printf 'Git est absent. Lancez xcode-select --install ou utilisez --install-tools.\n' >&2
  exit 1
fi

if ! command -v git-lfs >/dev/null 2>&1; then
  printf 'Git LFS est absent. Relancez avec --install-tools.\n' >&2
  exit 1
fi

if ! command -v dvc >/dev/null 2>&1; then
  printf 'DVC est absent. Relancez avec --install-tools.\n' >&2
  exit 1
fi

git lfs install --local --skip-repo
git lfs pull
git config --local pull.ff only
git config --local core.hooksPath .githooks

if [[ -n "$ASSET_REMOTE" ]]; then
  ASSET_ARGUMENTS=(configure "$ASSET_REMOTE")
  if [[ -n "$ASSET_ENDPOINT" ]]; then
    ASSET_ARGUMENTS+=(--endpoint "$ASSET_ENDPOINT")
  fi
  if [[ -n "$ASSET_PROFILE" ]]; then
    ASSET_ARGUMENTS+=(--profile "$ASSET_PROFILE")
  fi
  "$SCRIPT_DIR/assets-macos.sh" "${ASSET_ARGUMENTS[@]}"
fi

if dvc remote list 2>/dev/null | awk '$1 == "assets" { found=1 } END { exit !found }'; then
  "$SCRIPT_DIR/assets-macos.sh" pull
else
  printf "Remote d'assets non configuré — le test réseau fonctionne sans lui.\n"
fi

if [[ -x "$UNITY_EDITOR" ]]; then
  if SMART_MERGE="$(find_smart_merge)"; then
    git config --local merge.unityyamlmerge.name "Unity SmartMerge"
    git config --local merge.unityyamlmerge.driver "\"$SMART_MERGE\" merge -p %O %B %A %A"
    git config --local merge.unityyamlmerge.recursive binary
    printf 'UnityYAMLMerge configuré.\n'
  fi
elif (( OPEN_UNITY == 1 )); then
  printf "Ouverture de Unity Hub pour %s. Sélectionnez l'éditeur Apple Silicon.\n" "$UNITY_VERSION"
  open "unityhub://$UNITY_VERSION/$UNITY_CHANGESET"
fi

if [[ -x "$UNITY_EDITOR" ]]; then
  exec "$SCRIPT_DIR/doctor-macos.sh"
fi

"$SCRIPT_DIR/doctor-macos.sh" || true
printf "\nTerminez l'installation Unity dans Hub, puis relancez ./scripts/setup-macos.sh.\n"
