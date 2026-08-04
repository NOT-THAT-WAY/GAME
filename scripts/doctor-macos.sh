#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TOOLCHAIN_FILE="$REPO_ROOT/config/toolchain.env"
EXPECTED_UNITY="$(sed -n 's/^UNITY_VERSION=//p' "$TOOLCHAIN_FILE")"
EXPECTED_DVC_MAJOR="$(sed -n 's/^DVC_MAJOR_VERSION=//p' "$TOOLCHAIN_FILE")"
DEFAULT_EDITOR="/Applications/Unity/Hub/Editor/$EXPECTED_UNITY/Unity.app/Contents/MacOS/Unity"
UNITY_EDITOR="${GAME_UNITY_EDITOR:-$DEFAULT_EDITOR}"
ERROR_COUNT=0
WARNING_COUNT=0

ok() { printf '[OK]   %s\n' "$1"; }
warn() { printf '[WARN] %s\n' "$1"; WARNING_COUNT=$((WARNING_COUNT + 1)); }
fail() { printf '[FAIL] %s\n' "$1"; ERROR_COUNT=$((ERROR_COUNT + 1)); }

find_smart_merge() {
  local unity_contents candidate
  unity_contents="$(cd -- "$(dirname -- "$UNITY_EDITOR")/.." && pwd)"

  for candidate in \
    "$unity_contents/Helpers/UnityYAMLMerge" \
    "$unity_contents/Tools/UnityYAMLMerge"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

printf 'GAME doctor — macOS\nProjet: %s\nUnity attendue: %s\n\n' "$REPO_ROOT" "$EXPECTED_UNITY"

if [[ "$(uname -s)" == "Darwin" ]]; then
  ok "macOS détecté ($(uname -m))"
else
  fail "Ce diagnostic est réservé à macOS"
fi

case "$REPO_ROOT" in
  *iCloud*|*OneDrive*|*Dropbox*|*Google\ Drive*) warn "Le dépôt semble placé dans un dossier synchronisé" ;;
  *) ok "Dépôt hors des dossiers synchronisés courants" ;;
esac

if command -v git >/dev/null 2>&1; then
  ok "$(git --version)"
else
  fail "Git absent"
fi

if command -v git-lfs >/dev/null 2>&1; then
  ok "$(git lfs version)"
else
  fail "Git LFS absent"
fi

if command -v dvc >/dev/null 2>&1; then
  DVC_VERSION="$(dvc --version)"
  if [[ "$DVC_VERSION" == "$EXPECTED_DVC_MAJOR".* ]]; then
    ok "DVC $DVC_VERSION"
  else
    fail "DVC majeur $EXPECTED_DVC_MAJOR attendu, version trouvée: $DVC_VERSION"
  fi
else
  fail "DVC absent"
fi

if [[ -d "/Applications/Unity Hub.app" ]]; then
  ok "Unity Hub installé"
else
  fail "Unity Hub absent"
fi

if [[ -x "$UNITY_EDITOR" ]]; then
  ok "Unity $EXPECTED_UNITY trouvé"
  if SMART_MERGE="$(find_smart_merge)"; then
    ok "UnityYAMLMerge trouvé"
  else
    SMART_MERGE=""
    fail "UnityYAMLMerge introuvable dans l'installation Unity"
  fi
else
  fail "Unity $EXPECTED_UNITY absent (ou GAME_UNITY_EDITOR incorrect)"
  SMART_MERGE=""
fi

cd -- "$REPO_ROOT"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  ok "Dépôt Git valide"
else
  fail "Le dossier n'est pas un dépôt Git"
fi

if command -v git-lfs >/dev/null 2>&1 && git lfs env >/dev/null 2>&1; then
  ok "Git LFS initialisé pour le dépôt"
else
  fail "Git LFS n'est pas initialisé"
fi

LFS_ATTRIBUTE="$(git check-attr filter -- Assets/_Project/Test.png 2>/dev/null || true)"
if [[ "$LFS_ATTRIBUTE" == *": lfs" ]]; then
  ok "Règles Git LFS actives"
else
  fail "Les règles Git LFS ne s'appliquent pas"
fi

if [[ -f ".dvc/config" ]]; then
  ok "Projet DVC initialisé"
else
  fail "Configuration .dvc/config absente"
fi

if command -v dvc >/dev/null 2>&1 && dvc remote list 2>/dev/null | awk '$1 == "assets" { found=1 } END { exit !found }'; then
  ok "Remote externe 'assets' configuré localement"
else
  DVC_POINTER_COUNT="$(git ls-files '*.dvc' | grep -v '^\.dvc/' | wc -l | tr -d ' ')"
  if (( DVC_POINTER_COUNT > 0 )); then
    fail "Des assets DVC existent mais le remote 'assets' n'est pas configuré"
  else
    warn "Remote externe 'assets' non configuré — aucun master n'est encore requis"
  fi
fi

FORBIDDEN_TRACKED="$(git ls-files | awk 'BEGIN{IGNORECASE=1} /(^|\/)(Library|Temp|Obj|Logs|UserSettings|Build|Builds)(\/|$)/ {print}' | head -n 5)"
if [[ -z "$FORBIDDEN_TRACKED" ]]; then
  ok "Aucun cache Unity suivi par Git"
else
  fail "Caches Unity suivis par Git: $FORBIDDEN_TRACKED"
fi

MERGE_DRIVER="$(git config --local --get merge.unityyamlmerge.driver 2>/dev/null || true)"
if [[ -n "$MERGE_DRIVER" ]]; then
  ok "UnityYAMLMerge configuré dans ce dépôt"
elif [[ -n "$SMART_MERGE" ]]; then
  warn "UnityYAMLMerge existe mais le driver Git n'est pas configuré; relancer setup-macos.sh"
else
  warn "Le driver Smart Merge sera configuré après l'installation Unity"
fi

HOOKS_PATH="$(git config --local --get core.hooksPath 2>/dev/null || true)"
if [[ "$HOOKS_PATH" == ".githooks" ]]; then
  if [[ -x ".githooks/pre-commit" && -x ".githooks/pre-push" ]]; then
    ok "Gardes-fous commit/push et hook Git LFS activés"
  else
    fail "Hooks partagés absents ou non exécutables"
  fi
else
  warn "Gardes-fous Git inactifs; relancer setup-macos.sh"
fi

if [[ -d "/Applications/Wwise Launcher.app" ]] || [[ -d "/Applications/Audiokinetic/Wwise Launcher.app" ]]; then
  ok "Wwise Launcher présent (requis à la gate audio)"
else
  warn "Wwise Launcher non installé — normal avant la gate audio"
fi

if [[ -d "/Applications/Steam.app" ]]; then
  ok "Steam présent (requis à la gate Steam)"
else
  warn "Steam non installé — normal avant la gate Steam"
fi

if [[ -z "$(git config --get user.name 2>/dev/null || true)" ]] || [[ -z "$(git config --get user.email 2>/dev/null || true)" ]]; then
  warn "Nom ou email Git non configuré"
else
  ok "Identité Git configurée"
fi

printf '\nRésultat: %d erreur(s), %d avertissement(s).\n' "$ERROR_COUNT" "$WARNING_COUNT"
if (( ERROR_COUNT > 0 )); then
  exit 1
fi
