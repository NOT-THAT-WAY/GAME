#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TOOLCHAIN_FILE="$REPO_ROOT/config/toolchain.env"
UNITY_VERSION="$(sed -n 's/^UNITY_VERSION=//p' "$TOOLCHAIN_FILE")"
UNITY_EDITOR="${GAME_UNITY_EDITOR:-/Applications/Unity/Hub/Editor/$UNITY_VERSION/Unity.app/Contents/MacOS/Unity}"
ROLE="${1:-}"
ADDRESS="127.0.0.1"
ADDRESS_SET=0
PORT="7770"
PLAYER_NAME="$(git -C "$REPO_ROOT" config --get user.name 2>/dev/null || hostname -s)"
SKIP_BUILD=0
BUILD_ONLY=0
PROFILE="connection"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/first-test-macos.sh host [--profile connection|maze] [--name NAME] [--port 7770] [--skip-build]
  ./scripts/first-test-macos.sh client --address HOST_IP [--profile connection|maze] [--name NAME] [--port 7770] [--skip-build]
  ./scripts/first-test-macos.sh manual [--profile connection|maze] [--skip-build]
  ./scripts/first-test-macos.sh host --build-only

Profils:
  connection  roster FishNet minimal, preuve du jalon M0 (par défaut)
  maze        labyrinthe 16x16 jouable avec personnage déplaçable
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
      ADDRESS_SET=1
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
    --profile)
      (( $# >= 2 )) || fail "--profile attend connection ou maze."
      PROFILE="$(printf '%s' "$2" | tr '[:upper:]' '[:lower:]')"
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

case "$PROFILE" in
  connection)
    BUILD_METHOD="NotThatWay.Game.Editor.ConnectionTestBuild.BuildMac"
    BUILD_PATH="$REPO_ROOT/Builds/ConnectionTest/macOS/GAME-Connection-Test.app"
    BUILD_RELATIVE_PATH="Builds/ConnectionTest/macOS/GAME-Connection-Test.app"
    LOG_DIRECTORY="$REPO_ROOT/Logs/ConnectionTest"
    BUILD_LOG_RELATIVE_PATH="Logs/ConnectionTest/build-macos.log"
    PROFILE_LABEL="test de connexion"
    ;;
  maze)
    BUILD_METHOD="NotThatWay.Game.Editor.MazePlaytestBuild.BuildMac"
    BUILD_PATH="$REPO_ROOT/Builds/MazePlaytest/macOS/GAME-Maze-Playtest.app"
    BUILD_RELATIVE_PATH="Builds/MazePlaytest/macOS/GAME-Maze-Playtest.app"
    LOG_DIRECTORY="$REPO_ROOT/Logs/MazePlaytest"
    BUILD_LOG_RELATIVE_PATH="Logs/MazePlaytest/build-macos.log"
    PROFILE_LABEL="labyrinthe jouable"
    ;;
  *) fail "Le profil doit être connection ou maze." ;;
esac

[[ "$PORT" =~ ^[0-9]+$ ]] || fail "Le port doit être numérique."
(( PORT >= 1 && PORT <= 65535 )) || fail "Le port doit être compris entre 1 et 65535."
if [[ "$ROLE" == "client" && "$ADDRESS_SET" == "0" ]]; then
  fail "Un client doit recevoir --address HOST_IP (ou --address 127.0.0.1 pour un test local)."
fi
[[ -x "$UNITY_EDITOR" ]] || fail "Unity $UNITY_VERSION introuvable. Relancez setup-macos.sh."

cd -- "$REPO_ROOT"
"$SCRIPT_DIR/doctor-macos.sh"
"$SCRIPT_DIR/validate-repository.sh"

BUILD_BINARY="$BUILD_PATH/Contents/MacOS/GAME"
BUILD_MANIFEST_PATH="$(dirname -- "$BUILD_PATH")/build-manifest.json"
BUILD_LOG="$REPO_ROOT/$BUILD_LOG_RELATIVE_PATH"
GIT_COMMIT="$(git rev-parse HEAD 2>/dev/null || printf 'unknown')"
if [[ -n "$(git status --porcelain=v1 2>/dev/null || true)" ]]; then
  DIRTY_WORKTREE=true
else
  DIRTY_WORKTREE=false
fi
BUILD_STARTED_AT_UTC="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

write_build_manifest() {
  local result="$1"
  local exit_code="$2"
  local provenance="$3"
  local include_artifact="$4"
  local finished_at_json=null
  local binary_hash_json=null
  local binary_size_json=null
  local binary_hash
  local binary_size

  if [[ "$result" != "building" ]]; then
    finished_at_json="\"$(date -u '+%Y-%m-%dT%H:%M:%SZ')\""
  fi

  if [[ "$include_artifact" == "1" ]]; then
    [[ -x "$BUILD_BINARY" ]] || return 1
    binary_hash="$(shasum -a 256 "$BUILD_BINARY" 2>/dev/null | awk '{print $1}')"
    [[ "$binary_hash" =~ ^[0-9a-f]{64}$ ]] || return 1
    binary_size="$(wc -c < "$BUILD_BINARY" | tr -d '[:space:]')"
    [[ "$binary_size" =~ ^[0-9]+$ ]] || return 1
    binary_hash_json="\"$binary_hash\""
    binary_size_json="$binary_size"
  fi

  mkdir -p "$(dirname -- "$BUILD_MANIFEST_PATH")"
  cat > "$BUILD_MANIFEST_PATH" <<EOF
{
  "schemaVersion": 1,
  "kind": "unity-player-build",
  "profile": "$PROFILE",
  "platform": "macos",
  "buildTarget": "StandaloneOSX",
  "developmentBuild": true,
  "scriptingBackendPolicy": "project-default",
  "startedAtUtc": "$BUILD_STARTED_AT_UTC",
  "finishedAtUtc": $finished_at_json,
  "sourceGitCommit": "$GIT_COMMIT",
  "sourceDirtyWorktree": $DIRTY_WORKTREE,
  "unityVersion": "$UNITY_VERSION",
  "buildMethod": "$BUILD_METHOD",
  "buildPath": "$BUILD_RELATIVE_PATH",
  "binaryPath": "$BUILD_RELATIVE_PATH/Contents/MacOS/GAME",
  "binarySha256": $binary_hash_json,
  "binarySizeBytes": $binary_size_json,
  "buildLog": "$BUILD_LOG_RELATIVE_PATH",
  "provenance": "$provenance",
  "result": "$result",
  "exitCode": $exit_code
}
EOF
}

if (( SKIP_BUILD == 0 )); then
  mkdir -p "$LOG_DIRECTORY"
  printf 'Build macOS du %s...\n' "$PROFILE_LABEL"
  write_build_manifest "building" 0 "current-run" 0
  set +e
  "$UNITY_EDITOR" \
    -batchmode \
    -quit \
    -projectPath "$REPO_ROOT" \
    -executeMethod "$BUILD_METHOD" \
    -logFile "$BUILD_LOG"
  BUILD_EXIT_CODE=$?
  set -e
  if (( BUILD_EXIT_CODE != 0 )); then
    write_build_manifest "failed" "$BUILD_EXIT_CODE" "current-run" 0
    fail "Le build Unity a échoué. Voir $BUILD_LOG"
  fi
fi

if [[ ! -d "$BUILD_PATH" || ! -x "$BUILD_BINARY" ]]; then
  if (( SKIP_BUILD == 0 )); then
    write_build_manifest "failed" 1 "artifact-invalid" 0
  fi
  fail "Build absent ou binaire non exécutable: $BUILD_PATH"
fi

if (( SKIP_BUILD == 0 )); then
  if ! write_build_manifest "passed" 0 "current-run" 1; then
    write_build_manifest "failed" 1 "artifact-hash-failed" 0
    fail "Impossible de calculer le hash du binaire construit."
  fi
  printf 'Manifeste: %s\n' "$BUILD_MANIFEST_PATH"
elif [[ ! -f "$BUILD_MANIFEST_PATH" ]]; then
  printf 'Avertissement: build réutilisé sans manifeste de provenance: %s\n' "$BUILD_PATH" >&2
fi

if (( BUILD_ONLY == 1 )); then
  printf 'Build prêt: %s\n' "$BUILD_PATH"
  exit 0
fi

mkdir -p "$LOG_DIRECTORY"
PLAYER_LOG="$LOG_DIRECTORY/player-${ROLE}-$(date +%Y%m%d-%H%M%S).log"
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
