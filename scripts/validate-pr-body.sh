#!/usr/bin/env bash
set -euo pipefail

BODY_FILE="${1:-}"

if [[ -z "$BODY_FILE" ]]; then
  printf 'Usage: %s FICHIER_CORPS_PR\n' "$0" >&2
  exit 2
fi

if [[ ! -f "$BODY_FILE" || ! -s "$BODY_FILE" ]]; then
  printf 'Corps de PR absent ou vide: %s\n' "$BODY_FILE" >&2
  exit 1
fi

if ! grep -Fqx '## Résultat' "$BODY_FILE"; then
  printf 'Le corps de PR doit contenir une section exacte "## Résultat".\n' >&2
  exit 1
fi

RESULT_SECTION="$(awk '
  /^## Résultat[[:space:]]*$/ { capture=1; next }
  /^## / { if (capture) exit }
  capture { print }
' "$BODY_FILE")"

MEANINGFUL_RESULT="$(printf '%s\n' "$RESULT_SECTION" | sed \
  -e '/^[[:space:]]*$/d' \
  -e '/^[[:space:]]*<!--.*-->[[:space:]]*$/d' \
  -e '/^Décrire ce qui est maintenant testable et l.issue associée\.$/d')"

if [[ -z "$MEANINGFUL_RESULT" ]]; then
  printf 'La section "## Résultat" doit décrire un résultat testable réel.\n' >&2
  exit 1
fi

if grep -Fqx "Décrire ce qui est maintenant testable et l'issue associée." "$BODY_FILE" || \
   grep -Fqx 'Décrire ce qui est maintenant testable et l’issue associée.' "$BODY_FILE" || \
   grep -Fqx 'Lister scènes, prefabs, ProjectSettings, Work Units, fichiers LFS, pointeurs DVC et éventuelle migration de données.' "$BODY_FILE"; then
  printf 'Le corps de PR contient encore un texte indicatif du template.\n' >&2
  exit 1
fi

if grep -Eiq '(^|[^[:alnum:]_])(TODO|TBD|À compléter|A compléter)([^[:alnum:]_]|$)' "$BODY_FILE"; then
  printf 'Le corps de PR contient un placeholder non résolu (TODO/TBD/à compléter).\n' >&2
  exit 1
fi

printf 'Corps de PR renseigné: %s\n' "$BODY_FILE"
