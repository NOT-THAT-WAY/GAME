#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TASK_TYPE="${1:-}"
TASK_NAME="${2:-}"

if [[ -z "$TASK_TYPE" || -z "$TASK_NAME" ]]; then
  printf 'Usage: %s TYPE nom-court\nExemple: %s feat player-movement\n' "$0" "$0" >&2
  exit 2
fi

BRANCH_NAME="$TASK_TYPE/$TASK_NAME"
"$SCRIPT_DIR/validate-branch-name.sh" "$BRANCH_NAME"

cd -- "$REPO_ROOT"
if [[ -n "$(git status --porcelain)" ]]; then
  printf 'Le dépôt contient des changements. Committez-les ou traitez-les avant de changer de tâche.\n' >&2
  git status --short >&2
  exit 1
fi

git switch main
git pull --ff-only
git switch -c "$BRANCH_NAME"

printf 'Branche prête: %s\n' "$BRANCH_NAME"
printf 'Quand le travail est committé: ./scripts/publish-task.sh "%s: résultat testable"\n' "$TASK_TYPE"
