#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BRANCH_NAME="${1:-}"
PR_TITLE="${2:-}"

if [[ -z "$BRANCH_NAME" || -z "$PR_TITLE" ]]; then
  printf 'Usage: %s BRANCHE "TYPE: titre de la PR"\n' "$0" >&2
  exit 2
fi

"$SCRIPT_DIR/validate-branch-name.sh" "$BRANCH_NAME"
BRANCH_TYPE="${BRANCH_NAME#refs/heads/}"
BRANCH_TYPE="${BRANCH_TYPE%%/*}"

if [[ ! "$PR_TITLE" =~ ^${BRANCH_TYPE}(\([a-z0-9][a-z0-9._-]*\))?:[[:space:]].+ ]]; then
  cat >&2 <<EOF
Titre de PR invalide: $PR_TITLE
La branche '$BRANCH_NAME' attend un titre commençant par '$BRANCH_TYPE: '.
Exemple: $BRANCH_TYPE: describe the testable result
EOF
  exit 1
fi

printf 'Workflow Git valide: %s -> %s\n' "$BRANCH_NAME" "$PR_TITLE"
