#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
MAC_WRAPPER="$REPO_ROOT/scripts/unity-tests-macos.sh"
WINDOWS_WRAPPER="$REPO_ROOT/scripts/unity-tests-windows.ps1"

fail() {
  printf 'Unity test wrapper contract failure: %s\n' "$1" >&2
  exit 1
}

[[ -x "$MAC_WRAPPER" ]] || fail "macOS wrapper missing or not executable"
[[ -f "$WINDOWS_WRAPPER" ]] || fail "Windows wrapper missing"
bash -n "$MAC_WRAPPER"

for required in \
  'test-run.json' \
  'schemaVersion' \
  'unity-test-run' \
  'gitCommit' \
  'dirtyWorktree' \
  'requestedSuite' \
  'unityExitCode' \
  'suites'; do
  grep -Fq -- "$required" "$MAC_WRAPPER" || fail "macOS wrapper missing $required"
  grep -Fq -- "$required" "$WINDOWS_WRAPPER" || fail "Windows wrapper missing $required"
done

"$MAC_WRAPPER" --help >/dev/null
printf 'Unity test wrapper contract passed.\n'
