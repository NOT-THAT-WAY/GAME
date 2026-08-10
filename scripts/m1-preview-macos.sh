#!/usr/bin/env bash
set -euo pipefail

# Contrôle visuel du banc M1. Les gates automatiques lisent des états et des
# logs : elles ne voient pas un matériau hors URP, un personnage absent ou une
# scène noire. Ces captures sont le seul contrôle qui regarde vraiment l'image.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TOOLCHAIN_FILE="$REPO_ROOT/config/toolchain.env"
UNITY_VERSION="$(sed -n 's/^UNITY_VERSION=//p' "$TOOLCHAIN_FILE")"
UNITY_EDITOR="${GAME_UNITY_EDITOR:-/Applications/Unity/Hub/Editor/$UNITY_VERSION/Unity.app/Contents/MacOS/Unity}"
PREVIEW_DIRECTORY="$REPO_ROOT/Logs/M1Playtest"
LOG_FILE="$PREVIEW_DIRECTORY/preview-unity.log"
BUILD_PATH="$REPO_ROOT/Builds/M1Playtest/macOS/GAME-M1-Playtest.app"
BUILD_BINARY="$BUILD_PATH/Contents/MacOS/GAME"
PLAYER_PORT=7799
PLAYER_CHECK=0

usage() {
  cat <<'EOF'
Usage:
  ./scripts/m1-preview-macos.sh [--player]

Génère la scène M1 et écrit les captures de contrôle dans Logs/M1Playtest/.

Options:
  --player   capture aussi l'écran du build macOS déjà compilé. L'éditeur résout
             des matériaux que le player ne résout pas : seule cette capture
             prouve ce qu'un humain verra.

Variables:
  GAME_UNITY_EDITOR   chemin absolu vers l'executable Unity
EOF
}

fail() {
  printf 'Erreur: %s\n' "$1" >&2
  exit 1
}

while (( $# > 0 )); do
  case "$1" in
    --player) PLAYER_CHECK=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Option inconnue: $1" ;;
  esac
done

[[ -n "$UNITY_VERSION" ]] || fail "UNITY_VERSION absente de config/toolchain.env."
[[ -x "$UNITY_EDITOR" ]] || fail "Unity $UNITY_VERSION introuvable: $UNITY_EDITOR"

mkdir -p "$PREVIEW_DIRECTORY"
rm -f "$PREVIEW_DIRECTORY"/*.png

# Unity doit garder son contexte graphique : le rendu hors écran est exactement
# ce que cette gate vérifie.
"$UNITY_EDITOR" \
  -batchmode -quit \
  -projectPath "$REPO_ROOT" \
  -executeMethod NotThatWay.Game.Editor.M1PlaytestBuild.RenderPreview \
  -logFile "$LOG_FILE" ||
  fail "Rendu M1 échoué. Log: $LOG_FILE"

for required in apercu-aerien.png apercu-duel.png apercu-premiere-personne.png; do
  [[ -s "$PREVIEW_DIRECTORY/$required" ]] || fail "Capture manquante: $required. Log: $LOG_FILE"
done

if (( PLAYER_CHECK == 1 )); then
  [[ -x "$BUILD_BINARY" ]] ||
    fail "Build M1 absent: $BUILD_PATH. Le produire avec ./scripts/m1-network-tests-macos.sh all --build"

  PLAYER_SHOT="$PREVIEW_DIRECTORY/apercu-player-host.png"
  PLAYER_LOG="$PREVIEW_DIRECTORY/preview-player.log"
  rm -f "$PLAYER_SHOT" "$PLAYER_LOG"

  "$BUILD_BINARY" \
    -logFile "$PLAYER_LOG" \
    -screen-width 1600 -screen-height 900 -screen-fullscreen 0 \
    --game-role host --game-port "$PLAYER_PORT" --game-name PREVIEW_HOST \
    --capture-screenshot "$PLAYER_SHOT" --capture-after 6 --capture-and-quit \
    >/dev/null 2>&1 &
  PLAYER_PID=$!

  DEADLINE=$((SECONDS + 90))
  while kill -0 "$PLAYER_PID" 2>/dev/null && (( SECONDS < DEADLINE )); do
    sleep 1
  done
  if kill -0 "$PLAYER_PID" 2>/dev/null; then
    kill "$PLAYER_PID" 2>/dev/null || true
    fail "Le player M1 n'a pas quitté après sa capture. Log: $PLAYER_LOG"
  fi

  [[ -s "$PLAYER_SHOT" ]] || fail "Capture player absente. Log: $PLAYER_LOG"
  grep -q '\[GAME-M1-SHOT\] captured' "$PLAYER_LOG" ||
    fail "Le player n'a pas confirmé sa capture. Log: $PLAYER_LOG"
fi

printf 'Captures M1 écrites dans %s\n' "$PREVIEW_DIRECTORY"
printf 'Les regarder avant de montrer un build à un humain.\n'
