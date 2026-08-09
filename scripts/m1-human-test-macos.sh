#!/usr/bin/env bash
set -o pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BUILD_PATH="$REPO_ROOT/Builds/M1Playtest/macOS/GAME-M1-Playtest.app"
BUILD_BINARY="$BUILD_PATH/Contents/MacOS/GAME"
PORT=7770
BUILD_REQUESTED=0
RESULTS_DIRECTORY=""
STARTUP_PIDS=()

usage() {
  printf '%s\n' \
    'Usage: ./scripts/m1-human-test-macos.sh [--build] [--port PORT] [--results-dir PATH]' \
    '' \
    'Lance un host puis un client M1 visibles. --build reconstruit et rejoue la gate automatique.'
}

cleanup_startup() {
  local pid
  for pid in "${STARTUP_PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup_startup EXIT INT TERM

wait_for_log() {
  local log_file="$1"
  local pattern="$2"
  local pid="$3"
  local timeout_seconds="$4"
  local deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    if rg -q "$pattern" "$log_file" 2>/dev/null; then
      return 0
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
      return 1
    fi
    sleep 0.1
  done
  return 1
}

while (( $# > 0 )); do
  case "$1" in
    --build) BUILD_REQUESTED=1; shift ;;
    --port)
      (( $# >= 2 )) || { usage >&2; exit 2; }
      PORT="$2"; shift 2 ;;
    --results-dir)
      (( $# >= 2 )) || { usage >&2; exit 2; }
      RESULTS_DIRECTORY="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Option inconnue: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ! "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1024 || PORT > 65535 )); then
  printf 'Port invalide: %s\n' "$PORT" >&2
  exit 2
fi
if [[ -z "$RESULTS_DIRECTORY" ]]; then
  RESULTS_DIRECTORY="$REPO_ROOT/Logs/HumanTest/M1-$(date -u '+%Y%m%dT%H%M%SZ')-$$"
elif [[ "$RESULTS_DIRECTORY" != /* ]]; then
  RESULTS_DIRECTORY="$REPO_ROOT/$RESULTS_DIRECTORY"
fi
mkdir -p "$RESULTS_DIRECTORY"

if (( BUILD_REQUESTED == 1 )); then
  if (( PORT <= 65522 )); then
    GATE_BASE_PORT=$((PORT + 10))
  else
    GATE_BASE_PORT=$((PORT - 10))
  fi
  "$SCRIPT_DIR/m1-network-tests-macos.sh" all \
    --build \
    --base-port "$GATE_BASE_PORT" \
    --results-dir "$RESULTS_DIRECTORY/automated-gate" || exit $?
fi
[[ -x "$BUILD_BINARY" ]] || {
  printf 'Build M1 absent. Relancer avec --build.\n' >&2
  exit 2
}
if command -v lsof >/dev/null 2>&1 && lsof -nP -iUDP:"$PORT" >/dev/null 2>&1; then
  printf 'Port UDP déjà utilisé: %s\n' "$PORT" >&2
  exit 2
fi

HOST_LOG="$RESULTS_DIRECTORY/host.log"
CLIENT_LOG="$RESULTS_DIRECTORY/client.log"
"$BUILD_BINARY" \
  -logFile "$HOST_LOG" \
  --game-role host --game-port "$PORT" --game-name HUMAN_HOST \
  >"$RESULTS_DIRECTORY/host.console.log" 2>&1 &
HOST_PID=$!
STARTUP_PIDS+=("$HOST_PID")

if ! wait_for_log "$HOST_LOG" 'Roster updated \(1 participant\(s\)\)' "$HOST_PID" 10; then
  printf 'Le host M1 ne s est pas déclaré prêt. Log: %s\n' "$HOST_LOG" >&2
  exit 1
fi

"$BUILD_BINARY" \
  -logFile "$CLIENT_LOG" \
  --game-role client --game-address 127.0.0.1 --game-port "$PORT" --game-name HUMAN_CLIENT \
  >"$RESULTS_DIRECTORY/client.console.log" 2>&1 &
CLIENT_PID=$!
STARTUP_PIDS+=("$CLIENT_PID")

if ! wait_for_log "$HOST_LOG" 'Roster updated \(2 participant\(s\)\)' "$HOST_PID" 10 ||
   ! wait_for_log "$CLIENT_LOG" 'first_snapshot ' "$CLIENT_PID" 10 ||
   ! wait_for_log "$CLIENT_LOG" 'target_snapshot .*record=(added|duplicate)\.' "$CLIENT_PID" 10; then
  printf 'La paire M1 ne s est pas synchronisée. Logs: %s\n' "$RESULTS_DIRECTORY" >&2
  exit 1
fi

trap - EXIT INT TERM

printf '\nM1 lancé. Logs: %s\n\n' "$RESULTS_DIRECTORY"
printf '%s\n' \
  'Quête 1 — fenêtre par fenêtre, chacun rejoint le pad coloré opposé. PASS si aucun blocage/reset.' \
  'Quête 2 — côté pad rouge, près du pivot orange, maintenir E 2 s. PASS si le mur cyan devient horizontal sur les deux fenêtres.' \
  'Quête 3 — au même endroit, maintenir encore E 2 s. PASS si le mur revient vertical sur les deux fenêtres.' \
  'Quête 4 — sans déplacer ce pousseur, placer l autre joueur sur le pad vert puis répéter E 2 s. PASS si le mur reste vertical et personne n est déplacé/coincé.' \
  '' \
  'Fermer les deux fenêtres dès ces quatre verdicts obtenus.'
