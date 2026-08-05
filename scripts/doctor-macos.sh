#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TOOLCHAIN_FILE="$REPO_ROOT/config/toolchain.env"
EXPECTED_UNITY="$(sed -n 's/^UNITY_VERSION=//p' "$TOOLCHAIN_FILE")"
EXPECTED_DVC_MAJOR="$(sed -n 's/^DVC_MAJOR_VERSION=//p' "$TOOLCHAIN_FILE")"
DVC_POINTER_COUNT=0
if command -v git >/dev/null 2>&1; then
  DVC_POINTER_COUNT="$(git -C "$REPO_ROOT" ls-files '*.dvc' 2>/dev/null | awk '!/^\.dvc\// { count++ } END { print count + 0 }')"
fi
DEFAULT_EDITOR="/Applications/Unity/Hub/Editor/$EXPECTED_UNITY/Unity.app/Contents/MacOS/Unity"
UNITY_EDITOR="${GAME_UNITY_EDITOR:-$DEFAULT_EDITOR}"
VSCODE_APP="/Applications/Visual Studio Code.app"
VSCODE_CLI="$VSCODE_APP/Contents/Resources/app/bin/code"
ERROR_COUNT=0
WARNING_COUNT=0
REMOTE_PLAY_REQUIRED=0

while (( $# > 0 )); do
  case "$1" in
    --remote-play) REMOTE_PLAY_REQUIRED=1 ;;
    -h|--help)
      printf 'Usage: %s [--remote-play]\n' "$0"
      exit 0
      ;;
    *)
      printf 'Argument inconnu: %s\n' "$1" >&2
      exit 2
      ;;
  esac
  shift
done

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
  elif (( DVC_POINTER_COUNT > 0 )); then
    fail "DVC majeur $EXPECTED_DVC_MAJOR attendu, version trouvée: $DVC_VERSION"
  else
    warn "DVC $DVC_VERSION présent mais hors version attendue — optionnel avant le premier master"
  fi
elif (( DVC_POINTER_COUNT > 0 )); then
  fail "DVC absent alors que des masters sont référencés"
else
  warn "DVC absent — normal avant le premier master"
fi

if [[ -d "/Applications/Unity Hub.app" ]]; then
  ok "Unity Hub installé"
else
  fail "Unity Hub absent"
fi

if [[ -d "$VSCODE_APP" ]]; then
  ok "Visual Studio Code installé"
  if [[ -x "$VSCODE_CLI" ]]; then
    VSCODE_EXTENSIONS="$("$VSCODE_CLI" --list-extensions 2>/dev/null || true)"
    MISSING_VSCODE_EXTENSIONS=""
    for extension_id in \
      visualstudiotoolsforunity.vstuc \
      ms-dotnettools.csharp \
      ms-dotnettools.csdevkit; do
      if ! printf '%s\n' "$VSCODE_EXTENSIONS" | grep -Fxiq -- "$extension_id"; then
        MISSING_VSCODE_EXTENSIONS="${MISSING_VSCODE_EXTENSIONS}${MISSING_VSCODE_EXTENSIONS:+, }$extension_id"
      fi
    done

    if [[ -z "$MISSING_VSCODE_EXTENSIONS" ]]; then
      ok "Extensions VS Code Unity et C# installées"
    else
      fail "Extensions VS Code absentes: $MISSING_VSCODE_EXTENSIONS (relancer setup-macos.sh)"
    fi
  else
    fail "CLI interne de Visual Studio Code introuvable"
  fi
else
  fail "Visual Studio Code absent (relancer setup-macos.sh --install-tools)"
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

if TAILSCALE_STATUS="$("$SCRIPT_DIR/tailscale-macos.sh" status 2>/dev/null)"; then
  ok "$TAILSCALE_STATUS"
elif (( REMOTE_PLAY_REQUIRED == 1 )); then
  fail "Tailscale absent ou déconnecté — requis pour jouer depuis plusieurs réseaux"
else
  warn "Tailscale absent ou déconnecté — requis uniquement pour le test à distance"
fi

if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
  ok "FFmpeg et ffprobe présents (preuves animation/vidéo du studio Blender)"
else
  warn "FFmpeg ou ffprobe absent — requis pour les preuves animation/vidéo du studio Blender; relancer setup-macos.sh --install-tools"
fi

if [[ -d "/Applications/Wwise Launcher.app" ]] || [[ -d "/Applications/Audiokinetic/Wwise Launcher.app" ]]; then
  ok "Wwise Launcher présent (poste audio de Nils)"
else
  warn "Wwise Launcher absent — normal hors poste audio de Nils"
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
