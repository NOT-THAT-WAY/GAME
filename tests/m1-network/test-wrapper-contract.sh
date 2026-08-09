#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
NETWORK_WRAPPER="$REPO_ROOT/scripts/m1-network-tests-macos.sh"
HUMAN_WRAPPER="$REPO_ROOT/scripts/m1-human-test-macos.sh"
RUNBOOK="$REPO_ROOT/docs/FIRST_HUMAN_TEST_RUNBOOK.md"

fail() {
  printf 'M1 wrapper contract failure: %s\n' "$1" >&2
  exit 1
}

[[ -x "$NETWORK_WRAPPER" ]] || fail "network wrapper missing or not executable"
[[ -x "$HUMAN_WRAPPER" ]] || fail "human wrapper missing or not executable"
bash -n "$NETWORK_WRAPPER"
bash -n "$HUMAN_WRAPPER"

for required in \
  'occupancy' \
  'opposition' \
  'latejoin' \
  'm1-network-suite' \
  'buildSha256' \
  'dirtyWorktree' \
  'target_snapshot' \
  'record=(added|duplicate)' \
  'Assertion failed' \
  'Exception:' \
  'Roster updated \([3-9][0-9]* participant' \
  'balanced_opposition' \
  'player_in_swept_arc'; do
  grep -Fq -- "$required" "$NETWORK_WRAPPER" || fail "network wrapper missing $required"
done

for required in \
  'Quête 1' \
  'Quête 2' \
  'Quête 3' \
  'Quête 4' \
  'Fermer les deux fenêtres'; do
  grep -Fq -- "$required" "$HUMAN_WRAPPER" || fail "human wrapper missing $required"
done

grep -Fq 'm1-network-tests-macos.sh all --build' "$RUNBOOK" || fail "automated gate absent"
grep -Fq 'm1-human-test-macos.sh' "$RUNBOOK" || fail "human launch absent"

"$NETWORK_WRAPPER" --help >/dev/null
"$HUMAN_WRAPPER" --help >/dev/null
printf 'M1 wrapper contract passed.\n'
