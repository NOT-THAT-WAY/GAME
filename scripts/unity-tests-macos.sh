#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TOOLCHAIN_FILE="$REPO_ROOT/config/toolchain.env"
UNITY_VERSION="$(sed -n 's/^UNITY_VERSION=//p' "$TOOLCHAIN_FILE")"
UNITY_EDITOR="${GAME_UNITY_EDITOR:-/Applications/Unity/Hub/Editor/$UNITY_VERSION/Unity.app/Contents/MacOS/Unity}"
SUITE="all"
RESULTS_DIRECTORY=""

usage() {
  cat <<'EOF'
Usage:
  ./scripts/unity-tests-macos.sh [all|editmode|playmode] [--results-dir PATH]

Variables:
  GAME_UNITY_EDITOR       chemin absolu vers l'executable Unity
  GAME_TEST_RESULTS_DIR   dossier de sortie, remplace par --results-dir
EOF
}

fail() {
  printf 'Erreur: %s\n' "$1" >&2
  exit 1
}

if (( $# > 0 )) && [[ "$1" != --* ]]; then
  SUITE="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  shift
fi

while (( $# > 0 )); do
  case "$1" in
    --results-dir)
      (( $# >= 2 )) || fail "--results-dir attend un chemin."
      RESULTS_DIRECTORY="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Option inconnue: $1"
      ;;
  esac
done

case "$SUITE" in
  all) TEST_PLATFORMS=(EditMode PlayMode) ;;
  editmode) TEST_PLATFORMS=(EditMode) ;;
  playmode) TEST_PLATFORMS=(PlayMode) ;;
  *) fail "La suite doit etre all, editmode ou playmode." ;;
esac

[[ -n "$UNITY_VERSION" ]] || fail "UNITY_VERSION absente de config/toolchain.env."
[[ -x "$UNITY_EDITOR" ]] || fail "Unity $UNITY_VERSION introuvable: $UNITY_EDITOR"

if [[ -z "$RESULTS_DIRECTORY" ]]; then
  RESULTS_DIRECTORY="${GAME_TEST_RESULTS_DIR:-Logs/Tests/macos/$(date +%Y%m%d-%H%M%S)-$$}"
fi
if [[ "$RESULTS_DIRECTORY" != /* ]]; then
  RESULTS_DIRECTORY="$REPO_ROOT/$RESULTS_DIRECTORY"
fi
mkdir -p -- "$RESULTS_DIRECTORY"

STARTED_AT_UTC="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
GIT_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || printf 'unknown')"
if [[ -n "$(git -C "$REPO_ROOT" status --porcelain=v1 2>/dev/null || true)" ]]; then
  DIRTY_WORKTREE=true
else
  DIRTY_WORKTREE=false
fi
SUITE_RECORDS=()

append_suite_record() {
  local name="$1"
  local result="$2"
  local unity_exit="$3"
  local total="$4"
  local passed="$5"
  local failed="$6"
  local stem="$7"

  SUITE_RECORDS+=("    {\"name\": \"$name\", \"result\": \"$result\", \"unityExitCode\": $unity_exit, \"total\": $total, \"passed\": $passed, \"failed\": $failed, \"xml\": \"$stem-results.xml\", \"log\": \"$stem.log\"}")
}

xml_attribute() {
  local attribute="$1"
  local file="$2"
  local value

  value="$(grep -m 1 '<test-run ' "$file" | sed -nE "s/.* ${attribute}=\"([^\"]*)\".*/\\1/p" || true)"
  if [[ "$value" =~ ^[0-9]+$ ]]; then
    printf '%s' "$value"
  else
    printf 'null'
  fi
}

write_manifest() {
  local run_result="passed"
  local finished_at_utc
  local first=1
  local record

  if (( overall_exit != 0 )); then
    run_result="failed"
  fi
  finished_at_utc="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  {
    printf '{\n'
    printf '  "schemaVersion": 1,\n'
    printf '  "kind": "unity-test-run",\n'
    printf '  "startedAtUtc": "%s",\n' "$STARTED_AT_UTC"
    printf '  "finishedAtUtc": "%s",\n' "$finished_at_utc"
    printf '  "gitCommit": "%s",\n' "$GIT_COMMIT"
    printf '  "dirtyWorktree": %s,\n' "$DIRTY_WORKTREE"
    printf '  "unityVersion": "%s",\n' "$UNITY_VERSION"
    printf '  "platform": "macos",\n'
    printf '  "requestedSuite": "%s",\n' "$SUITE"
    printf '  "result": "%s",\n' "$run_result"
    printf '  "exitCode": %d,\n' "$overall_exit"
    printf '  "suites": [\n'
    for record in "${SUITE_RECORDS[@]}"; do
      if (( first == 0 )); then
        printf ',\n'
      fi
      printf '%s' "$record"
      first=0
    done
    printf '\n  ]\n'
    printf '}\n'
  } > "$RESULTS_DIRECTORY/test-run.json"
}

printf 'GAME — tests Unity %s\n' "$UNITY_VERSION"
printf 'Projet: %s\n' "$REPO_ROOT"
printf 'Resultats: %s\n' "$RESULTS_DIRECTORY"

overall_exit=0
for platform in "${TEST_PLATFORMS[@]}"; do
  stem="$(printf '%s' "$platform" | tr '[:upper:]' '[:lower:]')"
  results_file="$RESULTS_DIRECTORY/$stem-results.xml"
  log_file="$RESULTS_DIRECTORY/$stem.log"

  printf '\n[%s] lancement...\n' "$platform"
  set +e
  "$UNITY_EDITOR" \
    -batchmode \
    -projectPath "$REPO_ROOT" \
    -runTests \
    -testPlatform "$platform" \
    -testResults "$results_file" \
    -logFile "$log_file"
  unity_exit=$?
  set -e

  if (( unity_exit != 0 )); then
    printf '[%s] ECHEC — Unity a retourne %d. Log: %s\n' "$platform" "$unity_exit" "$log_file" >&2
    if (( overall_exit == 0 )); then
      overall_exit=$unity_exit
    fi
    append_suite_record "$platform" "failed" "$unity_exit" null null null "$stem"
    continue
  fi

  if [[ ! -s "$results_file" ]]; then
    printf '[%s] ECHEC — XML absent ou vide. Log: %s\n' "$platform" "$log_file" >&2
    if (( overall_exit == 0 )); then
      overall_exit=1
    fi
    append_suite_record "$platform" "failed" 0 null null null "$stem"
    continue
  fi

  if ! grep -m 1 '<test-run ' "$results_file" | grep -q 'result="Passed"'; then
    printf '[%s] ECHEC — le XML ne declare pas la suite Passed: %s\n' "$platform" "$results_file" >&2
    if (( overall_exit == 0 )); then
      overall_exit=1
    fi
    append_suite_record "$platform" "failed" 0 \
      "$(xml_attribute total "$results_file")" \
      "$(xml_attribute passed "$results_file")" \
      "$(xml_attribute failed "$results_file")" \
      "$stem"
    continue
  fi

  summary="$(grep -m 1 '<test-run ' "$results_file" | sed 's/^[[:space:]]*//')"
  append_suite_record "$platform" "passed" 0 \
    "$(xml_attribute total "$results_file")" \
    "$(xml_attribute passed "$results_file")" \
    "$(xml_attribute failed "$results_file")" \
    "$stem"
  printf '[%s] OK — %s\n' "$platform" "$summary"
done

write_manifest

if (( overall_exit != 0 )); then
  printf '\nUne ou plusieurs suites ont echoue. Resultats: %s\n' "$RESULTS_DIRECTORY" >&2
  exit "$overall_exit"
fi

printf '\nToutes les suites demandees sont vertes. Resultats: %s\n' "$RESULTS_DIRECTORY"
