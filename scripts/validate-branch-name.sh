#!/usr/bin/env bash
set -euo pipefail

BRANCH_NAME="${1:-}"
ALLOW_MAIN="${2:-}"

if [[ -z "$BRANCH_NAME" ]]; then
  BRANCH_NAME="$(git branch --show-current)"
fi

if [[ -z "$BRANCH_NAME" ]]; then
  printf 'Branche introuvable (HEAD détachée). Créez une branche de tâche.\n' >&2
  exit 1
fi
BRANCH_NAME="${BRANCH_NAME#refs/heads/}"

if [[ "$BRANCH_NAME" == "main" ]]; then
  if [[ "$ALLOW_MAIN" == "--allow-main" ]]; then
    exit 0
  fi

  printf 'Ne travaillez pas sur main. Créez une branche de tâche.\n' >&2
  exit 1
fi

if (( ${#BRANCH_NAME} > 80 )); then
  printf 'Nom de branche trop long (%d caractères, maximum 80): %s\n' "${#BRANCH_NAME}" "$BRANCH_NAME" >&2
  exit 1
fi

if [[ ! "$BRANCH_NAME" =~ ^(feat|fix|art|audio|data|docs|chore)/[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  cat >&2 <<EOF
Nom de branche invalide: $BRANCH_NAME
Format attendu: TYPE/nom-court-en-minuscules
Types: feat, fix, art, audio, data, docs, chore
Exemple: feat/player-movement
EOF
  exit 1
fi
