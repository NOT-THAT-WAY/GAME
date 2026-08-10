#!/usr/bin/env bash
set -o pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BUILD_PATH="$REPO_ROOT/Builds/M1Playtest/macOS/GAME-M1-Playtest.app"
BUILD_BINARY="$BUILD_PATH/Contents/MacOS/GAME"
PORT=7770
BUILD_REQUESTED=0
PLAYERS=2
RESULTS_DIRECTORY=""
STARTUP_PIDS=()
LAUNCHED_PID=""

usage() {
  printf '%s\n' \
    'Usage: ./scripts/m1-human-test-macos.sh [--build] [--players 2|3] [--port PORT] [--results-dir PATH]' \
    '' \
    'Lance un host puis un ou deux clients M1 visibles.' \
    '--build reconstruit, rejoue la gate automatique et écrit les captures de contrôle.'
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

launch_visible_player() {
  local log_file="$1"
  local console_file="$2"
  shift 2

  if ! open -n "$BUILD_PATH" --args -logFile "$log_file" "$@" \
    >"$console_file" 2>&1; then
    return 1
  fi

  # LaunchServices rattache l'application à la session graphique (PPID 1),
  # ce qui évite que le runner du terminal ferme les fenêtres avec son groupe
  # de processus. On retrouve ensuite le vrai PID grâce au log unique.
  local deadline=$((SECONDS + 5))
  local pid=""
  while (( SECONDS < deadline )); do
    pid="$(ps -axo pid=,ppid=,command= | awk -v log_file="$log_file" '
      $2 == 1 && index($0, "/Contents/MacOS/GAME ") > 0 &&
      index($0, "-logFile " log_file) > 0 { print $1; exit }
    ')"
    if [[ "$pid" =~ ^[0-9]+$ ]]; then
      LAUNCHED_PID="$pid"
      return 0
    fi
    sleep 0.1
  done

  return 1
}

while (( $# > 0 )); do
  case "$1" in
    --build) BUILD_REQUESTED=1; shift ;;
    --players)
      (( $# >= 2 )) || { usage >&2; exit 2; }
      PLAYERS="$2"; shift 2 ;;
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
if [[ ! "$PLAYERS" =~ ^[0-9]+$ ]] || (( PLAYERS < 2 || PLAYERS > 3 )); then
  printf 'Nombre de joueurs invalide: %s (attendu: 2 ou 3)\n' "$PLAYERS" >&2
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

  # Les gates lisent des états et des logs ; elles ne voient pas l'image. Un
  # build montré à un humain doit d'abord avoir été regardé.
  "$SCRIPT_DIR/m1-preview-macos.sh" --player || exit $?
  mkdir -p "$RESULTS_DIRECTORY/preview"
  cp "$REPO_ROOT"/Logs/M1Playtest/*.png "$RESULTS_DIRECTORY/preview/" || exit $?
  printf 'Captures de contrôle: %s\n' "$RESULTS_DIRECTORY/preview"
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
if ! launch_visible_player \
  "$HOST_LOG" \
  "$RESULTS_DIRECTORY/host.console.log" \
  --game-role host --game-port "$PORT" --game-name HUMAN_HOST; then
  printf 'Impossible de lancer le host M1 via LaunchServices.\n' >&2
  exit 1
fi
HOST_PID="$LAUNCHED_PID"
STARTUP_PIDS+=("$HOST_PID")

if ! wait_for_log "$HOST_LOG" 'Roster updated \(1 participant\(s\)\)' "$HOST_PID" 10; then
  printf 'Le host M1 ne s est pas déclaré prêt. Log: %s\n' "$HOST_LOG" >&2
  exit 1
fi

for (( CLIENT_NUMBER=1; CLIENT_NUMBER < PLAYERS; CLIENT_NUMBER++ )); do
  if (( CLIENT_NUMBER == 1 )); then
    CLIENT_STEM="client"
  else
    CLIENT_STEM="client-$CLIENT_NUMBER"
  fi
  CLIENT_LOG="$RESULTS_DIRECTORY/$CLIENT_STEM.log"
  if ! launch_visible_player \
    "$CLIENT_LOG" \
    "$RESULTS_DIRECTORY/$CLIENT_STEM.console.log" \
    --game-role client --game-address 127.0.0.1 --game-port "$PORT" \
    --game-name "HUMAN_CLIENT_$CLIENT_NUMBER"; then
    printf 'Impossible de lancer le client M1 %s via LaunchServices.\n' \
      "$CLIENT_NUMBER" >&2
    exit 1
  fi
  CLIENT_PID="$LAUNCHED_PID"
  STARTUP_PIDS+=("$CLIENT_PID")
  EXPECTED_ROSTER=$((CLIENT_NUMBER + 1))

  if ! wait_for_log "$HOST_LOG" "Roster updated \\($EXPECTED_ROSTER participant\\(s\\)\\)" "$HOST_PID" 10 ||
     ! wait_for_log "$CLIENT_LOG" 'first_snapshot ' "$CLIENT_PID" 10 ||
     ! wait_for_log "$CLIENT_LOG" 'target_snapshot .*record=(added|duplicate)\.' "$CLIENT_PID" 10; then
    printf 'Le groupe M1 ne s est pas synchronisé à %s joueur(s). Logs: %s\n' \
      "$EXPECTED_ROSTER" "$RESULTS_DIRECTORY" >&2
    exit 1
  fi
done

trap - EXIT INT TERM

printf '\nM1 lancé à %s joueurs. Logs: %s\n\n' "$PLAYERS" "$RESULTS_DIRECTORY"
if (( PLAYERS == 3 )); then
  printf '%s\n' \
    'Quête 1 — fenêtre par fenêtre, déplacer chaque joueur puis le rapprocher du centre. PASS si les trois répondent sans blocage/reset et leurs mouvements sont visibles à distance.' \
    'Quête 2 — côté pad rouge, au contact et face au mur cyan, donner trois coups au rythme du bras. PASS si deux ne suffisent pas et si le troisième le fait basculer sur les trois fenêtres.' \
    'Quête 3 — contourner le mur par le couloir nord puis maintenir E. PASS si la jauge progresse et si le mur revient à la verticale ; depuis le sud il ne doit pas repartir.' \
    'Quête 4 — laisser un joueur immobile dans l arc pendant qu un autre pousse. PASS si le mur l écarte sans le traverser ni le coincer.' \
    '' \
    'Fermer les trois fenêtres dès ces quatre verdicts obtenus.'
else
  printf '%s\n' \
    'Quête 1 — fenêtre par fenêtre, chacun rejoint le pad coloré opposé. PASS si aucun blocage/reset.' \
    'Quête 2 — côté pad rouge, au contact et face au mur cyan, donner trois coups au rythme du bras. PASS si deux ne suffisent pas et si le troisième le fait basculer sur les deux fenêtres.' \
    'Quête 3 — contourner le mur par le couloir nord puis maintenir E. PASS si la jauge progresse et si le mur revient à la verticale ; depuis le sud il ne doit pas repartir.' \
    'Quête 4 — rester immobile dans l arc pendant que l autre pousse. PASS si le mur écarte le joueur sans le traverser ni le coincer.' \
    '' \
    'Fermer les deux fenêtres dès ces quatre verdicts obtenus.'
fi
