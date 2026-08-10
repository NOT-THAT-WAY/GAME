#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
BRANCH_VALIDATOR="$REPO_ROOT/scripts/validate-pr-policy.sh"
BODY_VALIDATOR="$REPO_ROOT/scripts/validate-pr-body.sh"

fail() {
  printf 'Workflow contract failure: %s\n' "$1" >&2
  exit 1
}

expect_failure() {
  if "$@" >/dev/null 2>&1; then
    fail "command unexpectedly passed: $*"
  fi
}

TEMP_DIRECTORY="$(mktemp -d)"
trap 'rm -rf -- "$TEMP_DIRECTORY"' EXIT

VALID_BODY="$TEMP_DIRECTORY/valid.md"
TEMPLATE_BODY="$TEMP_DIRECTORY/template.md"
EMPTY_RESULT_BODY="$TEMP_DIRECTORY/empty-result.md"

cp "$REPO_ROOT/.github/PULL_REQUEST_TEMPLATE.md" "$TEMPLATE_BODY"
sed \
  -e 's/Décrire ce qui est maintenant testable et l.issue associée\./Le wrapper refuse désormais un corps de PR non renseigné./' \
  -e 's/Lister scènes, prefabs, ProjectSettings, Work Units, fichiers LFS, pointeurs DVC et éventuelle migration de données\./Aucun fichier Unity, Wwise, LFS ou DVC modifié./' \
  "$TEMPLATE_BODY" > "$VALID_BODY"
sed '/Décrire ce qui est maintenant testable et l.issue associée\./d' \
  "$TEMPLATE_BODY" > "$EMPTY_RESULT_BODY"

"$BRANCH_VALIDATOR" "feat/player-movement" "feat: add tested movement" >/dev/null
expect_failure "$BRANCH_VALIDATOR" "feat/player-movement" "fix: wrong type"
"$BRANCH_VALIDATOR" \
  "dependabot/github_actions/github-actions-dependencies" \
  "chore(deps): bump the github-actions group" \
  "dependabot[bot]" >/dev/null
expect_failure "$BRANCH_VALIDATOR" \
  "dependabot/github_actions/github-actions-dependencies" \
  "chore(deps): bump the github-actions group" \
  "human"

"$BODY_VALIDATOR" "$VALID_BODY" >/dev/null
expect_failure "$BODY_VALIDATOR" "$TEMPLATE_BODY"
expect_failure "$BODY_VALIDATOR" "$EMPTY_RESULT_BODY"

grep -Fq -- '--body-file' "$REPO_ROOT/scripts/publish-task.sh" || fail "Bash publisher lacks --body-file"
grep -Fq -- 'BodyFile' "$REPO_ROOT/scripts/publish-task.ps1" || fail "PowerShell publisher lacks -BodyFile"
if grep -Fq -- '--body-file .github/PULL_REQUEST_TEMPLATE.md' \
  "$REPO_ROOT/scripts/publish-task.sh" "$REPO_ROOT/scripts/publish-task.ps1"; then
  fail "publisher still submits the untouched template"
fi

printf 'Workflow policy contract passed.\n'
