#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PR_TITLE="${1:-}"

if [[ -z "$PR_TITLE" ]]; then
  printf 'Usage: %s "TYPE: résultat testable"\n' "$0" >&2
  exit 2
fi

cd -- "$REPO_ROOT"
BRANCH_NAME="$(git branch --show-current)"
"$SCRIPT_DIR/validate-pr-policy.sh" "$BRANCH_NAME" "$PR_TITLE"

if [[ -n "$(git status --porcelain)" ]]; then
  printf 'Le dépôt contient des changements non commités. Vérifiez git status avant de publier.\n' >&2
  git status --short >&2
  exit 1
fi

"$SCRIPT_DIR/validate-repository.sh"
git push -u origin "$BRANCH_NAME"

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  if PR_URL="$(gh pr view "$BRANCH_NAME" --json url --jq .url 2>/dev/null)"; then
    printf 'PR déjà ouverte: %s\n' "$PR_URL"
  else
    gh pr create \
      --base main \
      --head "$BRANCH_NAME" \
      --title "$PR_TITLE" \
      --body-file .github/PULL_REQUEST_TEMPLATE.md
  fi
  exit 0
fi

REMOTE_URL="$(git remote get-url origin)"
REPOSITORY="$(printf '%s' "$REMOTE_URL" | sed -E 's#^git@github\.com:##; s#^https://github\.com/##; s#\.git$##')"
printf 'Branche poussée. GitHub CLI n’est pas connecté; ouvrez la PR ici:\n'
printf 'https://github.com/%s/compare/main...%s?expand=1\n' "$REPOSITORY" "$BRANCH_NAME"
