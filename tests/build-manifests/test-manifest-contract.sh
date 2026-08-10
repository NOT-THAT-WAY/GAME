#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
MAC_WRAPPER="$REPO_ROOT/scripts/first-test-macos.sh"
WINDOWS_WRAPPER="$REPO_ROOT/scripts/first-test-windows.ps1"
FINGERPRINT_TOOL="$REPO_ROOT/scripts/build-bundle-fingerprint.py"

fail() {
  printf 'Build manifest contract failure: %s\n' "$1" >&2
  exit 1
}

[[ -x "$MAC_WRAPPER" ]] || fail "macOS build wrapper missing or not executable"
[[ -f "$WINDOWS_WRAPPER" ]] || fail "Windows build wrapper missing"
[[ -x "$FINGERPRINT_TOOL" ]] || fail "bundle fingerprint tool missing or not executable"
bash -n "$MAC_WRAPPER"

for required in \
  'build-manifest.json' \
  'unity-player-build' \
  'schemaVersion' \
  'buildId' \
  'buildSetId' \
  'sourceGitCommit' \
  'sourceDirtyWorktree' \
  'unityVersion' \
  'buildTarget' \
  'developmentBuild' \
  'binarySha256' \
  'binarySizeBytes' \
  'bundlePath' \
  'bundleFingerprintPath' \
  'bundleFingerprint' \
  'GAME_BUILD_ID' \
  'GAME_BUILD_SET_ID' \
  'GAME_SOURCE_GIT_COMMIT' \
  'provenance' \
  'current-run' \
  'artifact-invalid' \
  'artifact-hash-failed'; do
  grep -Fq -- "$required" "$MAC_WRAPPER" || fail "macOS wrapper missing $required"
  grep -Fq -- "$required" "$WINDOWS_WRAPPER" || fail "Windows wrapper missing $required"
done

# Bash et PowerShell n'ecrivent pas le schema avec la meme syntaxe.
grep -Fq '"schemaVersion": 2' "$MAC_WRAPPER" || fail "macOS manifest schema must be 2"
grep -Fq 'schemaVersion = 2' "$WINDOWS_WRAPPER" || fail "Windows manifest schema must be 2"
grep -Fq 'bundleManifestSha256' "$FINGERPRINT_TOOL" || fail "fingerprint output missing bundle hash"
grep -Fq 'bundleManifestSha256' "$WINDOWS_WRAPPER" || fail "Windows fingerprint output missing bundle hash"

grep -Fq 'shasum -a 256' "$MAC_WRAPPER" || fail "macOS wrapper does not hash the launch binary"
grep -Fq 'Get-FileHash -LiteralPath $BuildPath -Algorithm SHA256' "$WINDOWS_WRAPPER" || \
  fail "Windows wrapper does not hash the launch binary"

if grep -Fq 'write_build_manifest "passed"' "$MAC_WRAPPER" && \
   ! grep -Fq 'write_build_manifest "building"' "$MAC_WRAPPER"; then
  fail "macOS wrapper can leave a stale passed manifest during a rebuild"
fi
if grep -Fq 'Write-BuildManifest -Result "passed"' "$WINDOWS_WRAPPER" && \
   ! grep -Fq 'Write-BuildManifest -Result "building"' "$WINDOWS_WRAPPER"; then
  fail "Windows wrapper can leave a stale passed manifest during a rebuild"
fi

"$MAC_WRAPPER" manual --help >/dev/null
printf 'Build manifest contract passed.\n'
