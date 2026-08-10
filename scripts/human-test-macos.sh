#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TOOLCHAIN_FILE="$REPO_ROOT/config/toolchain.env"

PROFILE="maze"
PORT="7770"
BUILD_REQUESTED=0
PREFLIGHT_ONLY=0
TWO_INSTANCES=0
WARNINGS=()
BLOCKERS=()
BUILD_PRODUCED_BY_WRAPPER=0

usage() {
  cat <<'EOF'
Usage:
  ./scripts/human-test-macos.sh [--profile maze|connection] [--port 7770] [--build] [--two-instances] [--preflight-only]

Sans option, lance une instance hôte locale HT_HOST depuis le build existant.
--two-instances ajoute un client HT_CLIENT sur loopback. --build reconstruit
d'abord le profil avec le script de build du dépôt.

HT-00 est un smoke test humain local minimum. Ce n'est pas une preuve réseau finale.
EOF
}

add_warning() {
  WARNINGS+=("$1")
}

add_blocker() {
  BLOCKERS+=("$1")
}

json_codes() {
  local first=1
  local code

  printf '['
  for code in "$@"; do
    if (( first == 0 )); then
      printf ', '
    fi
    printf '"%s"' "$code"
    first=0
  done
  printf ']'
}

while (( $# > 0 )); do
  case "$1" in
    --profile)
      if (( $# < 2 )); then
        printf 'Erreur: --profile attend maze ou connection.\n' >&2
        exit 2
      fi
      PROFILE="$(printf '%s' "$2" | tr '[:upper:]' '[:lower:]')"
      shift 2
      ;;
    --port)
      if (( $# < 2 )); then
        printf 'Erreur: --port attend un nombre.\n' >&2
        exit 2
      fi
      PORT="$2"
      shift 2
      ;;
    --build)
      BUILD_REQUESTED=1
      shift
      ;;
    --preflight-only)
      PREFLIGHT_ONLY=1
      shift
      ;;
    --two-instances)
      TWO_INSTANCES=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Erreur: option inconnue: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$PROFILE" in
  maze)
    BUILD_RELATIVE_PATH="Builds/MazePlaytest/macOS/GAME-Maze-Playtest.app"
    BUILD_COMMAND_HINT='./scripts/first-test-macos.sh manual --profile maze --build-only'
    ;;
  connection)
    BUILD_RELATIVE_PATH="Builds/ConnectionTest/macOS/GAME-Connection-Test.app"
    BUILD_COMMAND_HINT='./scripts/first-test-macos.sh manual --profile connection --build-only'
    ;;
  *)
    printf 'Erreur: --profile doit être maze ou connection.\n' >&2
    exit 2
    ;;
esac

if [[ ! "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1 || PORT > 65535 )); then
  printf 'Erreur: --port doit être compris entre 1 et 65535.\n' >&2
  exit 2
fi

cd -- "$REPO_ROOT"

if [[ "$(uname -s 2>/dev/null || true)" != "Darwin" ]]; then
  add_blocker "WRONG_PLATFORM"
fi

if [[ ! -f "$TOOLCHAIN_FILE" ]]; then
  UNITY_VERSION="unknown"
  add_blocker "TOOLCHAIN_MISSING"
else
  UNITY_VERSION="$(sed -n 's/^UNITY_VERSION=//p' "$TOOLCHAIN_FILE")"
  if [[ -z "$UNITY_VERSION" ]]; then
    UNITY_VERSION="unknown"
    add_blocker "UNITY_VERSION_MISSING"
  fi
fi

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
  if [[ -z "$GIT_COMMIT" ]]; then
    GIT_COMMIT="unknown"
    add_blocker "GIT_COMMIT_UNAVAILABLE"
  fi

  if [[ -n "$(git status --porcelain=v1 2>/dev/null || true)" ]]; then
    add_warning "DIRTY_WORKTREE"
  fi
else
  GIT_COMMIT="unknown"
  add_blocker "GIT_UNAVAILABLE"
fi

SHORT_COMMIT="${GIT_COMMIT:0:8}"
[[ -n "$SHORT_COMMIT" ]] || SHORT_COMMIT="unknown"
STARTED_AT_UTC="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
SESSION_STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
SESSION_ID="ht00-${SESSION_STAMP}-${SHORT_COMMIT}-${RANDOM}"
SESSION_RELATIVE_PATH="Logs/HumanTest/$SESSION_ID"
SESSION_DIRECTORY="$REPO_ROOT/$SESSION_RELATIVE_PATH"

if ! mkdir -p "$SESSION_DIRECTORY"; then
  printf 'HT-00 readiness: BLOCKED\n'
  printf 'Blocage: SESSION_DIRECTORY_UNWRITABLE\n' >&2
  exit 2
fi

PREFLIGHT_LOG="$SESSION_DIRECTORY/preflight.log"
MANIFEST_PATH="$SESSION_DIRECTORY/manifest.json"
OBSERVATION_PATH="$SESSION_DIRECTORY/observation.md"
HOST_LOG="$SESSION_DIRECTORY/host.log"
CLIENT_LOG="$SESSION_DIRECTORY/client.log"

if (( TWO_INSTANCES == 1 )); then
  INSTANCE_COUNT=2
  TRANSPORT_SCOPE="two-instance-loopback"
  PLAYER_LABELS_JSON='["HT_HOST", "HT_CLIENT"]'
  CLIENT_LOG_ARTIFACT_JSON="\"$SESSION_RELATIVE_PATH/client.log\""
else
  INSTANCE_COUNT=1
  TRANSPORT_SCOPE="single-host-local"
  PLAYER_LABELS_JSON='["HT_HOST"]'
  CLIENT_LOG_ARTIFACT_JSON='null'
fi

printf 'HT-00 local preflight — %s\n' "$STARTED_AT_UTC" > "$PREFLIGHT_LOG"

if [[ -x "$SCRIPT_DIR/validate-repository.sh" ]]; then
  if ! "$SCRIPT_DIR/validate-repository.sh" >> "$PREFLIGHT_LOG" 2>&1; then
    add_warning "REPOSITORY_VALIDATION_FAILED"
  fi
else
  add_warning "REPOSITORY_VALIDATOR_MISSING"
fi

if command -v git-lfs >/dev/null 2>&1; then
  if ! git lfs fsck >> "$PREFLIGHT_LOG" 2>&1; then
    add_warning "LFS_VALIDATION_FAILED"
  fi
else
  add_warning "GIT_LFS_UNAVAILABLE"
fi

if (( BUILD_REQUESTED == 1 )); then
  if [[ ! -x "$SCRIPT_DIR/first-test-macos.sh" ]]; then
    add_blocker "BUILD_WRAPPER_MISSING"
  elif "$SCRIPT_DIR/first-test-macos.sh" manual --profile "$PROFILE" --build-only >> "$PREFLIGHT_LOG" 2>&1; then
    BUILD_PRODUCED_BY_WRAPPER=1
  else
    add_blocker "BUILD_FAILED"
  fi
else
  add_warning "BUILD_PROVENANCE_UNVERIFIED"
fi

BUILD_PATH="$REPO_ROOT/$BUILD_RELATIVE_PATH"
BUILD_BINARY="$BUILD_PATH/Contents/MacOS/GAME"
BUILD_HASH="unavailable"

if [[ ! -d "$BUILD_PATH" || ! -x "$BUILD_BINARY" ]]; then
  add_blocker "BUILD_MISSING_OR_NOT_EXECUTABLE"
else
  BUILD_HASH="$(shasum -a 256 "$BUILD_BINARY" 2>/dev/null | awk '{print $1}')"
  if [[ -z "$BUILD_HASH" ]]; then
    BUILD_HASH="unavailable"
    add_blocker "BUILD_HASH_FAILED"
  fi
fi

if command -v lsof >/dev/null 2>&1; then
  if lsof -nP -iUDP:"$PORT" >/dev/null 2>&1; then
    add_blocker "UDP_PORT_IN_USE"
  fi
else
  add_warning "PORT_AVAILABILITY_UNCHECKED"
fi

if ! command -v open >/dev/null 2>&1; then
  add_blocker "APP_LAUNCHER_MISSING"
fi

readiness_status() {
  if (( ${#BLOCKERS[@]} > 0 )); then
    printf 'BLOCKED'
  elif (( ${#WARNINGS[@]} > 0 )); then
    printf 'READY-WITH-WARNINGS'
  else
    printf 'READY'
  fi
}

write_manifest() {
  local readiness="$1"
  local launch_status="$2"
  local warnings_json='[]'
  local blockers_json='[]'

  if (( ${#WARNINGS[@]} > 0 )); then
    warnings_json="$(json_codes "${WARNINGS[@]}")"
  fi
  if (( ${#BLOCKERS[@]} > 0 )); then
    blockers_json="$(json_codes "${BLOCKERS[@]}")"
  fi

  cat > "$MANIFEST_PATH" <<EOF
{
  "schemaVersion": 1,
  "testId": "HT-00",
  "evidenceLevel": "developer-smoke",
  "isFinalNetworkProof": false,
  "sessionId": "$SESSION_ID",
  "startedAtUtc": "$STARTED_AT_UTC",
  "gitCommit": "$GIT_COMMIT",
  "unityVersion": "$UNITY_VERSION",
  "platform": "macos",
  "architecture": "$(uname -m 2>/dev/null || printf 'unknown')",
  "profile": "$PROFILE",
  "transportScope": "$TRANSPORT_SCOPE",
  "instanceCount": $INSTANCE_COUNT,
  "port": $PORT,
  "buildPath": "$BUILD_RELATIVE_PATH",
  "launchBinarySha256": "$BUILD_HASH",
  "buildProducedByWrapper": $([[ "$BUILD_PRODUCED_BY_WRAPPER" == "1" ]] && printf 'true' || printf 'false'),
  "readiness": "$readiness",
  "warnings": $warnings_json,
  "blockers": $blockers_json,
  "launchStatus": "$launch_status",
  "playerLabels": $PLAYER_LABELS_JSON,
  "artifacts": {
    "preflight": "$SESSION_RELATIVE_PATH/preflight.log",
    "hostLog": "$SESSION_RELATIVE_PATH/host.log",
    "clientLog": $CLIENT_LOG_ARTIFACT_JSON,
    "observation": "$SESSION_RELATIVE_PATH/observation.md",
    "report": "$SESSION_RELATIVE_PATH/report.json"
  }
}
EOF
}

write_observation() {
  local readiness="$1"
  local warning_lines="- aucun"
  local instance_check
  local code

  if (( ${#WARNINGS[@]} > 0 )); then
    warning_lines=""
    for code in "${WARNINGS[@]}"; do
      warning_lines="${warning_lines}- ${code}"$'\n'
    done
    warning_lines="${warning_lines%$'\n'}"
  fi

  if (( TWO_INSTANCES == 1 )); then
    instance_check='- [ ] Les deux fenêtres sont actives et le déplacement de `HT_HOST` est visible dans `HT_CLIENT`.'
  else
    instance_check='- [ ] La fenêtre `HT_HOST` est active.'
  fi

  cat > "$OBSERVATION_PATH" <<EOF
# HT-00 — smoke test minimum

- Session : \`$SESSION_ID\`
- Commit : \`$GIT_COMMIT\`
- Profil : \`$PROFILE\`
- Plateforme : macOS
- Instances : \`$INSTANCE_COUNT\`
- Préparation : **$readiness**
- Binaire lancé : \`$BUILD_HASH\`

## Avertissements de préflight

$warning_lines

## Actions strictement nécessaires

$instance_check
- [ ] Bouger et regarder autour de soi.
- [ ] Sauter une fois.
- [ ] Faire tourner un pivot ou un mur mobile.
- [ ] Donner un coup de poing au bot et le toucher.
- [ ] Fermer le jeu.

## Note humaine facultative

- Problème cassé ou gênant :
- Étapes minimales pour le reproduire :

## Verdict automatique après fermeture

\`\`\`bash
python3 scripts/human-test-report.py --session "$SESSION_RELATIVE_PATH"
\`\`\`

Le rapport exige uniquement les actions ci-dessus et l’absence d’erreur fatale. Ce test ne prouve
ni le réseau distant, ni l’autorité serveur, ni la convergence multi-machine ou la performance finale.
Ne pas publier les logs bruts : ils peuvent contenir des chemins locaux ou d’autres données techniques.
EOF
}

READINESS="$(readiness_status)"
write_observation "$READINESS"

printf 'HT-00 readiness: %s\n' "$READINESS"
if (( ${#WARNINGS[@]} > 0 )); then
  printf 'Avertissements: %s\n' "${WARNINGS[*]}"
fi
if (( ${#BLOCKERS[@]} > 0 )); then
  printf 'Blocages: %s\n' "${BLOCKERS[*]}"
  printf 'Build attendu: %s\n' "$BUILD_COMMAND_HINT"
  write_manifest "$READINESS" "not-started"
  printf 'Session: %s\n' "$SESSION_RELATIVE_PATH"
  exit 2
fi

if (( PREFLIGHT_ONLY == 1 )); then
  write_manifest "$READINESS" "not-requested"
  printf 'Préflight uniquement. Session: %s\n' "$SESSION_RELATIVE_PATH"
  printf 'HT-00 reste un smoke local et ne constitue pas une preuve réseau finale.\n'
  exit 0
fi

if ! open -n "$BUILD_PATH" --args \
  --human-test \
  --game-role host \
  --game-address 127.0.0.1 \
  --game-port "$PORT" \
  --game-name HT_HOST \
  -logFile "$HOST_LOG"; then
  add_blocker "HOST_LAUNCH_FAILED"
fi

if (( ${#BLOCKERS[@]} == 0 && TWO_INSTANCES == 1 )); then
  sleep 1
  if ! open -n "$BUILD_PATH" --args \
    --human-test \
    --game-role client \
    --game-address 127.0.0.1 \
    --game-port "$PORT" \
    --game-name HT_CLIENT \
    -logFile "$CLIENT_LOG"; then
    add_blocker "CLIENT_LAUNCH_FAILED"
  fi
fi

READINESS="$(readiness_status)"
if (( ${#BLOCKERS[@]} > 0 )); then
  write_manifest "$READINESS" "failed"
  printf 'HT-00 readiness: BLOCKED\n'
  printf 'Blocages: %s\n' "${BLOCKERS[*]}"
  printf 'Fermez toute instance déjà ouverte, puis consultez %s.\n' "$PREFLIGHT_LOG"
  exit 2
fi

write_manifest "$READINESS" "started"
if (( TWO_INSTANCES == 1 )); then
  printf 'Deux instances locales lancées avec --human-test.\n'
else
  printf 'Instance hôte locale lancée avec --human-test.\n'
fi
printf 'Checklist minimale: %s\n' "$OBSERVATION_PATH"
printf 'Log privé: %s\n' "$HOST_LOG"
if (( TWO_INSTANCES == 1 )); then
  printf 'Log client privé: %s\n' "$CLIENT_LOG"
fi
printf 'Après fermeture: python3 scripts/human-test-report.py --session %s\n' "$SESSION_RELATIVE_PATH"
printf 'HT-00 est un smoke local : ce résultat ne valide pas le réseau final.\n'
