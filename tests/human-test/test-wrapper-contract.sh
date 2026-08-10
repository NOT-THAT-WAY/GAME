#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
MAC_WRAPPER="$REPO_ROOT/scripts/human-test-macos.sh"
WINDOWS_WRAPPER="$REPO_ROOT/scripts/human-test-windows.ps1"
RUNBOOK="$REPO_ROOT/docs/FIRST_HUMAN_TEST_RUNBOOK.md"
REPORTER="$REPO_ROOT/scripts/human-test-report.py"

fail() {
  printf 'HT-00 contract failure: %s\n' "$1" >&2
  exit 1
}

[[ -x "$MAC_WRAPPER" ]] || fail "macOS wrapper missing or not executable"
[[ -f "$WINDOWS_WRAPPER" ]] || fail "Windows wrapper missing"
[[ -f "$RUNBOOK" ]] || fail "runbook missing"
[[ -x "$REPORTER" ]] || fail "automatic report script missing or not executable"

bash -n "$MAC_WRAPPER"

for required in \
  'READY-WITH-WARNINGS' \
  'BLOCKED' \
  'BUILD_PROVENANCE_UNVERIFIED' \
  '--human-test' \
  '127.0.0.1' \
  'HT_HOST' \
  'HT_CLIENT' \
  'instanceCount' \
  'single-host-local' \
  'developer-smoke' \
  'isFinalNetworkProof'; do
  grep -Fq -- "$required" "$MAC_WRAPPER" || fail "macOS wrapper missing $required"
  grep -Fq -- "$required" "$WINDOWS_WRAPPER" || fail "Windows wrapper missing $required"
done

grep -Fq -- '--two-instances' "$MAC_WRAPPER" || fail "macOS wrapper missing --two-instances"
grep -Fq -- 'TwoInstances' "$WINDOWS_WRAPPER" || fail "Windows wrapper missing -TwoInstances"

if grep -Eq 'remote-test|tailscale' "$MAC_WRAPPER" "$WINDOWS_WRAPPER"; then
  fail "HT-00 must remain a local-loopback wrapper"
fi

grep -Fq 'Il ne valide pas Windows, le réseau distant' "$RUNBOOK" || fail "runbook lacks final-proof boundary"
grep -Fq 'Logs/HumanTest/<session-id>/' "$RUNBOOK" || fail "runbook lacks artifact location"
grep -Fq 'human-test-report.py' "$MAC_WRAPPER" || fail "macOS wrapper lacks report command"
grep -Fq 'human-test-report.py' "$WINDOWS_WRAPPER" || fail "Windows wrapper lacks report command"

"$MAC_WRAPPER" --help >/dev/null
"$REPORTER" --help >/dev/null
python3 "$REPO_ROOT/tests/human-test/test-report.py"
printf 'HT-00 wrapper contract passed.\n'
