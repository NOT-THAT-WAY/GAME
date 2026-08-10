#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
NETWORK_WRAPPER="$REPO_ROOT/scripts/m1-network-tests-macos.sh"
HUMAN_WRAPPER="$REPO_ROOT/scripts/m1-human-test-macos.sh"
PREVIEW_WRAPPER="$REPO_ROOT/scripts/m1-preview-macos.sh"
RUNBOOK="$REPO_ROOT/docs/FIRST_HUMAN_TEST_RUNBOOK.md"

fail() {
  printf 'M1 wrapper contract failure: %s\n' "$1" >&2
  exit 1
}

[[ -x "$NETWORK_WRAPPER" ]] || fail "network wrapper missing or not executable"
[[ -x "$HUMAN_WRAPPER" ]] || fail "human wrapper missing or not executable"
[[ -x "$PREVIEW_WRAPPER" ]] || fail "preview wrapper missing or not executable"
bash -n "$NETWORK_WRAPPER"
bash -n "$HUMAN_WRAPPER"
bash -n "$PREVIEW_WRAPPER"

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
  'torque_opposed' \
  'swept_player_pushed' \
  'rotation_started' \
  'quarter_turn'; do
  grep -Fq -- "$required" "$NETWORK_WRAPPER" || fail "network wrapper missing $required"
done

for required in \
  '--players 2|3' \
  'm1-preview-macos.sh' \
  'Quête 1' \
  'Quête 2' \
  'Quête 3' \
  'Quête 4' \
  'Quête 5' \
  'Fermer les deux fenêtres' \
  'Fermer les trois fenêtres'; do
  grep -Fq -- "$required" "$HUMAN_WRAPPER" || fail "human wrapper missing $required"
done

for required in \
  'M1PlaytestBuild.RenderPreview' \
  'apercu-aerien.png' \
  'apercu-duel.png' \
  'apercu-premiere-personne.png' \
  'apercu-player-host.png'; do
  grep -Fq -- "$required" "$PREVIEW_WRAPPER" || fail "preview wrapper missing $required"
done

grep -Fq '"$SCRIPT_DIR/m1-preview-macos.sh" --player' "$HUMAN_WRAPPER" ||
  fail "human --build must capture the real player"

# Le rendu hors écran est l'objet même du contrôle : le désactiver rendrait la
# capture aveugle exactement là où elle doit voir.
grep -Fq -- '-nographics' "$PREVIEW_WRAPPER" && fail "preview wrapper must render with graphics"

grep -Fq 'm1-network-tests-macos.sh all --build' "$RUNBOOK" || fail "automated gate absent"
grep -Fq 'm1-human-test-macos.sh' "$RUNBOOK" || fail "human launch absent"
grep -Fq 'm1-preview-macos.sh' "$RUNBOOK" || fail "visual check absent"

"$NETWORK_WRAPPER" --help >/dev/null
"$HUMAN_WRAPPER" --help >/dev/null
"$PREVIEW_WRAPPER" --help >/dev/null
printf 'M1 wrapper contract passed.\n'
