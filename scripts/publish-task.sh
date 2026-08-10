#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PR_TITLE="${1:-}"
BODY_FILE=""

if [[ -z "$PR_TITLE" ]]; then
  printf 'Usage: %s "TYPE: résultat testable" [--body-file FICHIER]\n' "$0" >&2
  exit 2
fi
shift

while (( $# > 0 )); do
  case "$1" in
    --body-file)
      if (( $# < 2 )); then
        printf 'Erreur: --body-file attend un chemin.\n' >&2
        exit 2
      fi
      BODY_FILE="$2"
      shift 2
      ;;
    *)
      printf 'Erreur: option inconnue: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

cd -- "$REPO_ROOT"
BRANCH_NAME="$(git branch --show-current)"
"$SCRIPT_DIR/validate-pr-policy.sh" "$BRANCH_NAME" "$PR_TITLE"

if [[ -n "$BODY_FILE" ]]; then
  "$SCRIPT_DIR/validate-pr-body.sh" "$BODY_FILE"
fi

if [[ -n "$(git status --porcelain)" ]]; then
  printf 'Le dépôt contient des changements non commités. Vérifiez git status avant de publier.\n' >&2
  git status --short >&2
  exit 1
fi

"$SCRIPT_DIR/validate-repository.sh"

GH_AUTHENTICATED=0
EXISTING_PR_URL=""
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  GH_AUTHENTICATED=1
  EXISTING_PR_URL="$(gh pr view "$BRANCH_NAME" --json url --jq .url 2>/dev/null || true)"
  if [[ -z "$EXISTING_PR_URL" && -z "$BODY_FILE" && ( ! -t 0 || ! -t 1 ) ]]; then
    printf 'Une nouvelle PR non interactive exige --body-file FICHIER.\n' >&2
    printf 'En terminal interactif, omettez cette option pour remplir le corps dans gh.\n' >&2
    exit 2
  fi
fi

git push -u origin "$BRANCH_NAME"

if (( GH_AUTHENTICATED == 1 )); then
  if [[ -n "$EXISTING_PR_URL" ]]; then
    printf 'PR déjà ouverte: %s\n' "$EXISTING_PR_URL"
  else
    CREATE_ARGS=(pr create --base main --head "$BRANCH_NAME" --title "$PR_TITLE")
    if [[ -n "$BODY_FILE" ]]; then
      CREATE_ARGS+=(--body-file "$BODY_FILE")
    fi
    gh "${CREATE_ARGS[@]}"
  fi
  exit 0
fi

REMOTE_URL="$(git remote get-url origin)"
REPOSITORY="$(printf '%s' "$REMOTE_URL" | sed -E 's#^git@github\.com:##; s#^https://github\.com/##; s#\.git$##')"
printf 'Branche poussée. GitHub CLI n’est pas connecté; ouvrez la PR ici:\n'
printf 'https://github.com/%s/compare/main...%s?expand=1\n' "$REPOSITORY" "$BRANCH_NAME"
