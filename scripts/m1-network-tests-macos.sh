#!/usr/bin/env bash
set -o pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TOOLCHAIN_FILE="$REPO_ROOT/config/toolchain.env"
SUITE="all"
BUILD_REQUESTED=0
BASE_PORT=7790
RESULTS_DIRECTORY=""
ACTIVE_PIDS=()
SCENARIOS=()

usage() {
  printf '%s\n' \
    'Usage: ./scripts/m1-network-tests-macos.sh [all|occupancy|opposition|latejoin] [options]' \
    '' \
    'Options:' \
    '  --build                 reconstruit le player Development M1 avant les tests' \
    '  --base-port PORT        premier port UDP (défaut: 7790)' \
    '  --results-dir PATH      dossier de preuves' \
    '' \
    'Trois scénarios locaux réels sont lancés en processus séparés. Aucun input' \
    'n est injecté hors du chemin FishNet Replicate/Reconcile.'
}

fail() {
  printf 'Erreur M1: %s\n' "$1" >&2
  return 1
}

cleanup() {
  local pid
  for pid in "${ACTIVE_PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT INT TERM

if (( $# > 0 )) && [[ "$1" != --* ]]; then
  SUITE="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  shift
fi
while (( $# > 0 )); do
  case "$1" in
    --build)
      BUILD_REQUESTED=1
      shift
      ;;
    --base-port)
      (( $# >= 2 )) || { usage >&2; exit 2; }
      BASE_PORT="$2"
      shift 2
      ;;
    --results-dir)
      (( $# >= 2 )) || { usage >&2; exit 2; }
      RESULTS_DIRECTORY="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Option inconnue: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$SUITE" in
  all) REQUESTED_SCENARIOS=(occupancy opposition latejoin) ;;
  occupancy|opposition|latejoin) REQUESTED_SCENARIOS=("$SUITE") ;;
  *) usage >&2; exit 2 ;;
esac
if [[ ! "$BASE_PORT" =~ ^[0-9]+$ ]] ||
   (( BASE_PORT < 1024 || BASE_PORT + ${#REQUESTED_SCENARIOS[@]} > 65535 )); then
  printf 'Le port de base doit être compris entre 1024 et 65532.\n' >&2
  exit 2
fi

UNITY_VERSION="$(sed -n 's/^UNITY_VERSION=//p' "$TOOLCHAIN_FILE")"
UNITY_EDITOR="${GAME_UNITY_EDITOR:-/Applications/Unity/Hub/Editor/$UNITY_VERSION/Unity.app/Contents/MacOS/Unity}"
BUILD_PATH="$REPO_ROOT/Builds/M1Playtest/macOS/GAME-M1-Playtest.app"
BUILD_BINARY="$BUILD_PATH/Contents/MacOS/GAME"
if [[ -z "$RESULTS_DIRECTORY" ]]; then
  RESULTS_DIRECTORY="$REPO_ROOT/Logs/Network/m1-suite/$(date -u '+%Y%m%dT%H%M%SZ')-$$"
elif [[ "$RESULTS_DIRECTORY" != /* ]]; then
  RESULTS_DIRECTORY="$REPO_ROOT/$RESULTS_DIRECTORY"
fi
mkdir -p "$RESULTS_DIRECTORY"

GIT_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || printf unknown)"
SOURCE_DIRTY=false
if [[ -n "$(git -C "$REPO_ROOT" status --porcelain=v1 2>/dev/null || true)" ]]; then
  SOURCE_DIRTY=true
fi
SHORT_COMMIT="${GIT_COMMIT:0:8}"
RUN_ID="m1-$(date -u '+%Y%m%dT%H%M%SZ')-${SHORT_COMMIT}-$$"
BUILD_STARTED_AT_UTC="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
BUILD_SET_SEED="schema=1|commit=$GIT_COMMIT|profile=m1|unity=$UNITY_VERSION"
if [[ "$SOURCE_DIRTY" == "true" ]]; then
  BUILD_SET_SEED="$BUILD_SET_SEED|dirty=true|started=$BUILD_STARTED_AT_UTC"
fi
EXPECTED_BUILD_SET_ID="$(printf '%s' "$BUILD_SET_SEED" | shasum -a 256 | awk '{print $1}')"
EXPECTED_BUILD_ID="$(printf '%s' "$EXPECTED_BUILD_SET_ID|platform=macos|started=$BUILD_STARTED_AT_UTC" | shasum -a 256 | awk '{print $1}')"

if (( BUILD_REQUESTED == 1 )); then
  [[ -x "$UNITY_EDITOR" ]] || { printf 'Unity introuvable: %s\n' "$UNITY_EDITOR" >&2; exit 2; }
  GAME_BUILD_ID="$EXPECTED_BUILD_ID" \
  GAME_BUILD_SET_ID="$EXPECTED_BUILD_SET_ID" \
  GAME_BUILD_PROFILE=m1 \
  GAME_BUILD_PLATFORM=macos \
  GAME_SOURCE_GIT_COMMIT="$GIT_COMMIT" \
  GAME_SOURCE_DIRTY_WORKTREE="$SOURCE_DIRTY" \
  GAME_BUILD_STARTED_AT_UTC="$BUILD_STARTED_AT_UTC" \
  GAME_UNITY_VERSION="$UNITY_VERSION" \
  "$UNITY_EDITOR" \
    -batchmode -quit \
    -projectPath "$REPO_ROOT" \
    -executeMethod NotThatWay.Game.Editor.M1PlaytestBuild.BuildMac \
    -logFile "$RESULTS_DIRECTORY/build.log"
  build_status=$?
  if (( build_status != 0 )); then
    printf 'Build M1 échoué (%d).\n' "$build_status" >&2
    exit "$build_status"
  fi
fi
[[ -x "$BUILD_BINARY" ]] || {
  printf 'Player M1 absent: %s (utiliser --build).\n' "$BUILD_BINARY" >&2
  exit 2
}

for offset in "${!REQUESTED_SCENARIOS[@]}"; do
  port=$((BASE_PORT + offset))
  if command -v lsof >/dev/null 2>&1 && lsof -nP -iUDP:"$port" >/dev/null 2>&1; then
    printf 'Port UDP déjà utilisé: %d\n' "$port" >&2
    exit 2
  fi
done

launch_player() {
  local label="$1"
  local log_file="$2"
  shift 2
  "$BUILD_BINARY" \
    -batchmode -nographics \
    -logFile "$log_file" \
    "$@" \
    >"${log_file%.log}.console.log" 2>&1 &
  LAUNCHED_PID=$!
  ACTIVE_PIDS+=("$LAUNCHED_PID")
  printf '[%s] pid=%d log=%s\n' "$label" "$LAUNCHED_PID" "$log_file"
}

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

log_match_count() {
  local log_file="$1"
  local pattern="$2"
  rg -c "$pattern" "$log_file" 2>/dev/null || printf '0\n'
}

wait_for_new_log_match() {
  local log_file="$1"
  local pattern="$2"
  local previous_count="$3"
  local pid="$4"
  local timeout_seconds="$5"
  local deadline=$((SECONDS + timeout_seconds))
  local current_count
  while (( SECONDS < deadline )); do
    current_count="$(log_match_count "$log_file" "$pattern")"
    if (( current_count > previous_count )); then
      return 0
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
      return 1
    fi
    sleep 0.1
  done
  return 1
}

wait_for_process() {
  local pid="$1"
  local timeout_seconds="$2"
  local deadline=$((SECONDS + timeout_seconds))
  while kill -0 "$pid" 2>/dev/null; do
    if (( SECONDS >= deadline )); then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      return 124
    fi
    sleep 0.1
  done
  wait "$pid"
}

verify_log() {
  local log_file="$1"
  local expected_name="$2"
  [[ -s "$log_file" ]] || fail "log absent: $log_file" || return 1
  [[ "$(rg -c '^\[GAME-BUILD\]' "$log_file" 2>/dev/null || true)" == "1" ]] ||
    fail "identité build absente ou dupliquée: $log_file" || return 1
  rg -q '^\[GAME-BUILD\].* profile=m1 platform=macos ' "$log_file" ||
    fail "identité build hors profil M1 macOS: $log_file" || return 1
  rg -q "\[GAME-M1-RESULT\] PASS name=${expected_name} run=${RUN_ID} reason=ok" "$log_file" ||
    fail "verdict PASS absent: $expected_name" || return 1
  if rg -q 'snapshot_rejected|history_miss|\[GAME-M1-RESULT\] FAIL' "$log_file" ||
     rg -q '(^|[[:space:]])[A-Za-z_][A-Za-z0-9_.]*Exception:' "$log_file" ||
     rg -qi 'Native Crash|Crash!!!|Assertion failed|\[GAME-CONNECTION\] ERREUR:|Tugboat.*(failed|failure|timed out|timeout)' "$log_file"; then
    fail "erreur runtime détectée: $log_file" || return 1
  fi
}

verify_same_build() {
  local first_log="$1"
  shift
  local expected
  expected="$(rg -o -m1 'buildId=[0-9a-f]{64}' "$first_log")"
  local log_file
  for log_file in "$@"; do
    [[ "$(rg -o -m1 'buildId=[0-9a-f]{64}' "$log_file")" == "$expected" ]] ||
      fail "buildId différent entre processus" || return 1
  done
}

run_occupancy() {
  local port="$1"
  local directory="$RESULTS_DIRECTORY/occupancy"
  mkdir -p "$directory"
  launch_player occupancy-host "$directory/host.log" \
    --game-role host --game-port "$port" --game-name M1_OCC_HOST \
    --m1-auto-player none --m1-test-name occupancy-host --m1-run-id "$RUN_ID" \
    --m1-evaluate-after-ready-seconds 16 --m1-auto-quit-seconds 19 \
    --m1-expect-players 2 --m1-expect-connections 2 \
    --m1-expect-rotation-min-mdeg 60000 --m1-expect-quarter-turns-min 1 \
    --m1-expect-swept-pushes-min 1
  # Le quart de tour est prouvé par --m1-expect-quarter-turns-min, qui compte les
  # franchissements. Le minimum de rotation porte, lui, sur l'angle au moment de
  # l'évaluation : depuis l'ADR 0005 le battant est contre-poussable dans les deux
  # sens, donc l'angle final est légitimement inférieur au pic — le pousseur
  # automatisé dépasse le bout du battant et le repousse un peu avant de décrocher.
  # Exiger 90000 sur l'angle final confondait « le quart de tour a eu lieu » et
  # « le battant s'est immobilisé au-delà », ce qui n'est vrai que pour un mur
  # non réversible, c'est-à-dire le modèle d'avant l'ADR 0005. Le plancher reste
  # élevé pour attraper un battant qui tournerait puis serait entièrement ramené.
  local host_pid="$LAUNCHED_PID"
  wait_for_log "$directory/host.log" 'Roster updated \(1 participant\(s\)\)' "$host_pid" 10 ||
    { fail 'host occupancy non prêt'; return 1; }
  # Battant alourdi (400 mdeg/tick, cf. docs/M1_WALL_HANDOFF.md étape 2) : à un
  # bras de levier de mi-longueur (~700 pour mille avec le plancher à 400), la
  # vitesse tombe à 16,8°/s, donc 5,36 s pour armer le quart de tour attendu ci-
  # dessus, contre 90 ticks (1,5 s) d'approche. Les fenêtres d'évaluation
  # suivent cette physique, pas seulement l'ancienne marge de connexion.
  launch_player occupancy-client "$directory/client.log" \
    --game-role client --game-address 127.0.0.1 --game-port "$port" --game-name M1_OCC_CLIENT \
    --m1-auto-player push-left --m1-test-name occupancy-client --m1-run-id "$RUN_ID" \
    --m1-evaluate-after-ready-seconds 13 --m1-auto-quit-seconds 16 \
    --m1-expect-players 2 --m1-expect-revision-min 1 \
    --m1-expect-snapshots-min 1 --m1-expect-target-snapshots-min 1
  local client_pid="$LAUNCHED_PID"
  local client_status=0 host_status=0
  wait_for_process "$client_pid" 28 || client_status=$?
  wait_for_process "$host_pid" 8 || host_status=$?
  (( client_status == 0 && host_status == 0 )) || return 1
  verify_log "$directory/host.log" occupancy-host || return 1
  verify_log "$directory/client.log" occupancy-client || return 1
  verify_same_build "$directory/host.log" "$directory/client.log" || return 1
  # Le host reste dans l'arc : le battant doit l'écarter et poursuivre sa course.
  rg -q 'rotation_started wall=10 direction=1' "$directory/host.log" || return 1
  rg -q 'swept_player_pushed wall=10' "$directory/host.log" || return 1
  rg -q 'quarter_turn wall=10' "$directory/host.log" || return 1
}

run_opposition() {
  local port="$1"
  local directory="$RESULTS_DIRECTORY/opposition"
  mkdir -p "$directory"
  launch_player opposition-host "$directory/host.log" \
    --game-role host --game-port "$port" --game-name M1_OPP_HOST \
    --m1-auto-player press-right --m1-test-name opposition-host --m1-run-id "$RUN_ID" \
    --m1-evaluate-after-ready-seconds 6 --m1-auto-quit-seconds 11 \
    --m1-expect-players 2 --m1-expect-connections 2 \
    --m1-expect-opposed-ticks-min 60 --m1-expect-rotation-max-mdeg 30000
  local host_pid="$LAUNCHED_PID"
  wait_for_log "$directory/host.log" 'Roster updated \(1 participant\(s\)\)' "$host_pid" 10 ||
    { fail 'host opposition non prêt'; return 1; }
  launch_player opposition-client "$directory/client.log" \
    --game-role client --game-address 127.0.0.1 --game-port "$port" --game-name M1_OPP_CLIENT \
    --m1-auto-player press-left --m1-test-name opposition-client --m1-run-id "$RUN_ID" \
    --m1-evaluate-after-ready-seconds 6 --m1-auto-quit-seconds 8 \
    --m1-expect-players 2 \
    --m1-expect-snapshots-min 1 --m1-expect-target-snapshots-min 1
  local client_pid="$LAUNCHED_PID"
  local client_status=0 host_status=0
  wait_for_process "$client_pid" 20 || client_status=$?
  wait_for_process "$host_pid" 5 || host_status=$?
  (( client_status == 0 && host_status == 0 )) || return 1
  verify_log "$directory/host.log" opposition-host || return 1
  verify_log "$directory/client.log" opposition-client || return 1
  verify_same_build "$directory/host.log" "$directory/client.log" || return 1
  # Deux bras de levier égaux et opposés : le couple net est nul et le battant
  # ne franchit aucun quart de tour.
  rg -q 'torque_opposed wall=10 sources=2' "$directory/host.log" || return 1
  ! rg -q 'quarter_turn wall=10' "$directory/host.log" || return 1
}

run_latejoin() {
  local port="$1"
  local directory="$RESULTS_DIRECTORY/latejoin"
  mkdir -p "$directory"
  launch_player latejoin-host "$directory/host.log" \
    --game-role host --game-port "$port" --game-name M1_LATE_HOST \
    --m1-auto-player clear-sweep --m1-test-name latejoin-host --m1-run-id "$RUN_ID" \
    --m1-evaluate-after-ready-seconds 18 --m1-auto-quit-seconds 24 \
    --m1-expect-players 2 --m1-expect-connections 2 \
    --m1-expect-rotation-min-mdeg 30000
  local host_pid="$LAUNCHED_PID"
  wait_for_log "$directory/host.log" 'Roster updated \(1 participant\(s\)\)' "$host_pid" 10 ||
    { fail 'host latejoin non prêt'; return 1; }
  local roster_one_count
  roster_one_count="$(log_match_count "$directory/host.log" 'Roster updated \(1 participant\(s\)\)')"
  launch_player latejoin-pusher "$directory/pusher.log" \
    --game-role client --game-address 127.0.0.1 --game-port "$port" --game-name M1_PUSHER \
    --m1-auto-player push-left --m1-test-name latejoin-pusher --m1-run-id "$RUN_ID" \
    --m1-evaluate-after-ready-seconds 9 --m1-auto-quit-seconds 10 \
    --m1-expect-players 2 --m1-expect-revision-min 1 --m1-expect-snapshots-min 1 \
    --m1-expect-target-snapshots-min 1
  local pusher_pid="$LAUNCHED_PID"
  wait_for_log "$directory/host.log" 'rotation_started wall=10' "$host_pid" 16 ||
    { fail 'rotation absente avant le départ du pousseur'; return 1; }
  local pusher_status=0
  wait_for_process "$pusher_pid" 20 || pusher_status=$?
  (( pusher_status == 0 )) || { fail 'pusher latejoin en échec'; return 1; }
  wait_for_new_log_match \
    "$directory/host.log" \
    'Roster updated \(1 participant\(s\)\)' \
    "$roster_one_count" \
    "$host_pid" \
    5 || { fail 'déconnexion pusher non confirmée'; return 1; }
  local roster_two_count
  roster_two_count="$(log_match_count "$directory/host.log" 'Roster updated \(2 participant\(s\)\)')"
  launch_player latejoin-observer "$directory/late.log" \
    --game-role client --game-address 127.0.0.1 --game-port "$port" --game-name M1_LATE_CLIENT \
    --m1-auto-player none --m1-test-name latejoin-observer --m1-run-id "$RUN_ID" \
    --m1-evaluate-after-ready-seconds 4 --m1-auto-quit-seconds 14 \
    --m1-expect-players 2 --m1-expect-revision-min 2 \
    --m1-expect-snapshots-min 1 --m1-expect-target-snapshots-min 1
  local late_pid="$LAUNCHED_PID"
  wait_for_new_log_match \
    "$directory/host.log" \
    'Roster updated \(2 participant\(s\)\)' \
    "$roster_two_count" \
    "$host_pid" \
    5 || { fail 'remplacement latejoin non confirmé'; return 1; }
  local host_status=0 late_status=0
  wait_for_process "$host_pid" 25 || host_status=$?
  wait_for_process "$late_pid" 5 || late_status=$?
  (( host_status == 0 && late_status == 0 )) || return 1
  verify_log "$directory/host.log" latejoin-host || return 1
  verify_log "$directory/pusher.log" latejoin-pusher || return 1
  verify_log "$directory/late.log" latejoin-observer || return 1
  verify_same_build "$directory/host.log" "$directory/pusher.log" "$directory/late.log" || return 1
  # L'arrivant reçoit un segment arrêté : même angle, même révision que l'hôte,
  # sans avoir vu passer un seul tick de la rotation.
  rg -q 'target_snapshot wall=10 angleMdeg=[0-9]+ revision=[0-9]+ .*rotating=False .*record=(added|duplicate)\.' "$directory/late.log" || return 1
  ! rg -q 'Roster updated \([3-9][0-9]* participant\(s\)\)' "$directory/host.log" || return 1
  # Le host dégage l'arc avant la poussée, et le pousseur n'est pas balayé par
  # le battant qu'il tient : personne ne doit être écarté.
  ! rg -q 'swept_player_pushed' "$directory/host.log" || return 1
}

printf 'M1 network suite — run=%s results=%s\n' "$RUN_ID" "$RESULTS_DIRECTORY"
overall_status=0
for offset in "${!REQUESTED_SCENARIOS[@]}"; do
  scenario="${REQUESTED_SCENARIOS[$offset]}"
  port=$((BASE_PORT + offset))
  printf '\n[%s] port=%d\n' "$scenario" "$port"
  if "run_$scenario" "$port"; then
    printf '[%s] PASS\n' "$scenario"
    SCENARIOS+=("$scenario")
  else
    printf '[%s] FAIL\n' "$scenario" >&2
    overall_status=1
    cleanup
    break
  fi
done

BUILD_SHA="$(shasum -a 256 "$BUILD_BINARY" | awk '{print $1}')"
BUNDLE_FINGERPRINT_PATH="$RESULTS_DIRECTORY/build-bundle-fingerprint.json"
python3 "$SCRIPT_DIR/build-bundle-fingerprint.py" \
  --root "$BUILD_PATH" \
  --output "$BUNDLE_FINGERPRINT_PATH" || overall_status=1
BUNDLE_MANIFEST_SHA="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["bundleManifestSha256"])' "$BUNDLE_FINGERPRINT_PATH")"
FIRST_HOST_LOG="$RESULTS_DIRECTORY/${REQUESTED_SCENARIOS[0]}/host.log"
BUILD_MARKER="$(rg -m1 '^\[GAME-BUILD\]' "$FIRST_HOST_LOG" 2>/dev/null || true)"
EMBEDDED_BUILD_ID="$(printf '%s' "$BUILD_MARKER" | sed -nE 's/.* buildId=([0-9a-f]{64}).*/\1/p')"
EMBEDDED_BUILD_SET_ID="$(printf '%s' "$BUILD_MARKER" | sed -nE 's/.* buildSetId=([0-9a-f]{64}).*/\1/p')"
EMBEDDED_COMMIT="$(printf '%s' "$BUILD_MARKER" | sed -nE 's/.* commit=([^ ]+).*/\1/p')"
EMBEDDED_DIRTY="$(printf '%s' "$BUILD_MARKER" | sed -nE 's/.* dirty=(true|false).*/\1/p')"
if (( BUILD_REQUESTED == 1 )) &&
   [[ "$EMBEDDED_BUILD_ID" != "$EXPECTED_BUILD_ID" ||
      "$EMBEDDED_BUILD_SET_ID" != "$EXPECTED_BUILD_SET_ID" ||
      "$EMBEDDED_COMMIT" != "$GIT_COMMIT" ||
      "$EMBEDDED_DIRTY" != "$SOURCE_DIRTY" ]]; then
  printf 'Identité embarquée différente du build courant.\n' >&2
  overall_status=1
fi
RESULT="passed"
(( overall_status == 0 )) || RESULT="failed"
{
  printf '{\n'
  printf '  "schemaVersion": 1,\n'
  printf '  "kind": "m1-network-suite",\n'
  printf '  "runId": "%s",\n' "$RUN_ID"
  printf '  "result": "%s",\n' "$RESULT"
  printf '  "requestedSuite": "%s",\n' "$SUITE"
  printf '  "gitCommit": "%s",\n' "$GIT_COMMIT"
  printf '  "dirtyWorktree": %s,\n' "$SOURCE_DIRTY"
  printf '  "workspaceGitCommit": "%s",\n' "$GIT_COMMIT"
  printf '  "workspaceDirtyAtStart": %s,\n' "$SOURCE_DIRTY"
  printf '  "embeddedBuildId": "%s",\n' "$EMBEDDED_BUILD_ID"
  printf '  "embeddedBuildSetId": "%s",\n' "$EMBEDDED_BUILD_SET_ID"
  printf '  "embeddedSourceGitCommit": "%s",\n' "$EMBEDDED_COMMIT"
  printf '  "embeddedSourceDirtyWorktree": %s,\n' "${EMBEDDED_DIRTY:-true}"
  printf '  "unityVersion": "%s",\n' "$UNITY_VERSION"
  printf '  "buildSha256": "%s",\n' "$BUILD_SHA"
  printf '  "bundleFingerprintPath": "build-bundle-fingerprint.json",\n'
  printf '  "bundleManifestSha256": "%s",\n' "$BUNDLE_MANIFEST_SHA"
  printf '  "scenariosPassed": ['
  for index in "${!SCENARIOS[@]}"; do
    (( index == 0 )) || printf ', '
    printf '"%s"' "${SCENARIOS[$index]}"
  done
  printf ']\n}\n'
} >"$RESULTS_DIRECTORY/manifest.json"

printf '\nM1 suite %s — %s\n' "$RESULT" "$RESULTS_DIRECTORY"
exit "$overall_status"
