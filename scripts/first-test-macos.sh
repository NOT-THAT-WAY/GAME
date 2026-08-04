#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TOOLCHAIN_FILE="$REPO_ROOT/config/toolchain.env"
UNITY_VERSION="$(sed -n 's/^UNITY_VERSION=//p' "$TOOLCHAIN_FILE")"
UNITY_EDITOR="${GAME_UNITY_EDITOR:-/Applications/Unity/Hub/Editor/$UNITY_VERSION/Unity.app/Contents/MacOS/Unity}"
BUILD_PATH="$REPO_ROOT/Builds/ConnectionTest/macOS/GAME-Connection-Test.app"
ROLE="${1:-}"
ADDRESS="127.0.0.1"
PORT="7770"
PLAYER_NAME="$(git -C "$REPO_ROOT" config --get user.name 2>/dev/null || hostname -s)"
SKIP_BUILD=0
BUILD_ONLY=0

usage() {
  cat <<'EOF'
Usage:
  ./scripts/first-test-macos.sh host [--name NAME] [--port 7770] [--skip-build]
  ./scripts/first-test-macos.sh client --address HOST_IP [--name NAME] [--port 7770] [--skip-build]
  ./scripts/first-test-macos.sh manual [--skip-build]
  ./scripts/first-test-macos.sh host --build-only
EOF
}

fail() {
  printf 'Erreur: %s\n' "$1" >&2
  exit 1
}

[[ -n "$ROLE" ]] || { usage; exit 2; }
ROLE="$(printf '%s' "$ROLE" | tr '[:upper:]' '[:lower:]')"
shift

while (( $# > 0 )); do
  case "$1" in
    --address)
      (( $# >= 2 )) || fail "--address attend l'IP de l'hôte."
      ADDRESS="$2"
      shift 2
      ;;
    --name)
      (( $# >= 2 )) || fail "--name attend un nom."
      PLAYER_NAME="$2"
      shift 2
      ;;
    --port)
      (( $# >= 2 )) || fail "--port attend un nombre."
      PORT="$2"
      shift 2
      ;;
    --skip-build) SKIP_BUILD=1; shift ;;
    --build-only) BUILD_ONLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Option inconnue: $1" ;;
  esac
done

case "$ROLE" in
  host|client|manual) ;;
  *) fail "Le rôle doit être host, client ou manual." ;;
esac

[[ "$PORT" =~ ^[0-9]+$ ]] || fail "Le port doit être numérique."
(( PORT >= 1 && PORT <= 65535 )) || fail "Le port doit être compris entre 1 et 65535."
if [[ "$ROLE" == "client" && "$ADDRESS" == "127.0.0.1" ]]; then
  fail "Un client sur une autre machine doit recevoir --address HOST_IP."
fi
[[ -x "$UNITY_EDITOR" ]] || fail "Unity $UNITY_VERSION introuvable. Relancez setup-macos.sh."

cd -- "$REPO_ROOT"
"$SCRIPT_DIR/validate-repository.sh"

if (( SKIP_BUILD == 0 )); then
  mkdir -p "$REPO_ROOT/Logs/ConnectionTest"
  printf 'Build macOS du test de connexion...\n'
  "$UNITY_EDITOR" \
    -batchmode \
    -quit \
    -projectPath "$REPO_ROOT" \
    -executeMethod NotThatWay.Game.Editor.ConnectionTestBuild.BuildMac \
    -logFile "$REPO_ROOT/Logs/ConnectionTest/build-macos.log"
fi

[[ -d "$BUILD_PATH" ]] || fail "Build absent: $BUILD_PATH"
if (( BUILD_ONLY == 1 )); then
  printf 'Build prêt: %s\n' "$BUILD_PATH"
  exit 0
fi

mkdir -p "$REPO_ROOT/Logs/ConnectionTest"
PLAYER_LOG="$REPO_ROOT/Logs/ConnectionTest/player-${ROLE}-$(date +%Y%m%d-%H%M%S).log"
open -n "$BUILD_PATH" --args \
  --game-role "$ROLE" \
  --game-address "$ADDRESS" \
  --game-port "$PORT" \
  --game-name "$PLAYER_NAME" \
  -logFile "$PLAYER_LOG"

printf 'Test lancé en %s sous le nom "%s". Log: %s\n' "$ROLE" "$PLAYER_NAME" "$PLAYER_LOG"
if [[ "$ROLE" == "host" ]]; then
  LOCAL_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
  printf 'Les clients utilisent le port UDP %s et cette IP probable: %s\n' "$PORT" "${LOCAL_IP:-à vérifier dans Réglages Réseau}"
fi
