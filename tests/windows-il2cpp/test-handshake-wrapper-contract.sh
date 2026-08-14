#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$REPO_ROOT/scripts/verify-il2cpp-handshake-windows.ps1"
GUARD="$REPO_ROOT/Assets/_Project/Runtime/FishNetVersionHandshakeGuard.cs"

fail() {
  printf 'Windows IL2CPP handshake contract failure: %s\n' "$1" >&2
  exit 1
}

[[ -f "$WRAPPER" ]] || fail "wrapper missing"
[[ -f "$GUARD" ]] || fail "runtime guard missing"

for required in \
  'M1PlaytestBuild.BuildWindows' \
  'GAME-M1-Playtest.exe' \
  'DIRTY_WORKTREE' \
  'PROJECT_SETTINGS_MUTATED' \
  'projectSettingsChanges' \
  'Authenticated as IL2CPP_PROBE' \
  'kicked for being on FishNet version' \
  '[GAME-FISHNET-HANDSHAKE]' \
  'HANDSHAKE_MARKERS_MISSING' \
  'clientBoundaryObserved' \
  'serverBoundaryObserved' \
  'launchBinarySha256' \
  'scriptingBackend = "IL2CPP"'; do
  grep -Fq -- "$required" "$WRAPPER" || fail "wrapper missing $required"
done

for required in \
  'CorrectedMalformedLength' \
  'observedLengthMarker == (byte)(expectedLengthMarker | 1)' \
  'packet.Count != expectedPacketLength' \
  'ENABLE_IL2CPP' \
  'server-incoming' \
  'client-outgoing'; do
  grep -Fq -- "$required" "$GUARD" || fail "guard missing $required"
done

printf 'Windows IL2CPP handshake wrapper contract passed.\n'
