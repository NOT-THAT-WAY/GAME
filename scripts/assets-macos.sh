#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REMOTE_NAME="assets"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/assets-macos.sh configure <remote-url> [--endpoint <url>] [--profile <name>]
  ./scripts/assets-macos.sh pull [target]
  ./scripts/assets-macos.sh push [target]
  ./scripts/assets-macos.sh track <ExternalAssets/Discipline/AssetId>
  ./scripts/assets-macos.sh smoke-init
  ./scripts/assets-macos.sh smoke-verify
  ./scripts/assets-macos.sh status

Le contenu lourd reste dans le remote DVC. Seuls les pointeurs .dvc vont dans Git.
EOF
}

fail() {
  printf 'Erreur: %s\n' "$1" >&2
  exit 1
}

require_dvc() {
  command -v dvc >/dev/null 2>&1 || fail "DVC est absent. Relancez setup-macos.sh --install-tools."
  [[ -f "$REPO_ROOT/.dvc/config" ]] || fail "Le dépôt DVC n'est pas initialisé."
}

remote_is_configured() {
  dvc remote list 2>/dev/null | awk -v name="$REMOTE_NAME" '$1 == name { found=1 } END { exit !found }'
}

require_remote() {
  remote_is_configured || fail "Remote '$REMOTE_NAME' non configuré. Lancez d'abord la commande configure."
}

ACTION="${1:-help}"
if (( $# > 0 )); then
  shift
fi

cd -- "$REPO_ROOT"
require_dvc

case "$ACTION" in
  configure)
    (( $# >= 1 )) || fail "Une URL de remote est requise."
    REMOTE_URL="$1"
    shift
    ENDPOINT_URL=""
    PROFILE=""

    while (( $# > 0 )); do
      case "$1" in
        --endpoint)
          (( $# >= 2 )) || fail "--endpoint attend une URL."
          ENDPOINT_URL="$2"
          shift 2
          ;;
        --profile)
          (( $# >= 2 )) || fail "--profile attend un nom."
          PROFILE="$2"
          shift 2
          ;;
        *) fail "Option inconnue: $1" ;;
      esac
    done

    dvc remote add --local --force --default "$REMOTE_NAME" "$REMOTE_URL"
    if [[ -n "$ENDPOINT_URL" ]]; then
      dvc remote modify --local "$REMOTE_NAME" endpointurl "$ENDPOINT_URL"
    fi
    if [[ -n "$PROFILE" ]]; then
      dvc remote modify --local "$REMOTE_NAME" profile "$PROFILE"
    fi
    printf "Remote DVC '%s' configuré localement. Aucun credential n'est ajouté à Git.\n" "$REMOTE_NAME"
    ;;

  pull)
    require_remote
    if (( $# > 0 )); then
      dvc pull --remote "$REMOTE_NAME" "$@"
    else
      dvc pull --remote "$REMOTE_NAME"
    fi
    ;;

  push)
    require_remote
    if (( $# > 0 )); then
      dvc push --remote "$REMOTE_NAME" "$@"
    else
      dvc push --remote "$REMOTE_NAME"
    fi
    printf 'Contenu envoyé. Committez maintenant les pointeurs .dvc et le registre avant git push.\n'
    ;;

  track)
    (( $# == 1 )) || fail "track attend exactement un chemin."
    [[ -e "$1" ]] || fail "Chemin introuvable: $1"

    TARGET_PARENT="$(cd -- "$(dirname -- "$1")" && pwd -P)"
    TARGET_ABSOLUTE="$TARGET_PARENT/$(basename -- "$1")"
    [[ ! -L "$TARGET_ABSOLUTE" ]] || fail "Les liens symboliques ne sont pas acceptés comme lots d'assets."

    case "$TARGET_ABSOLUTE" in
      "$REPO_ROOT"/ExternalAssets/*) ;;
      *) fail "Le lot doit être placé sous ExternalAssets/." ;;
    esac

    RELATIVE_PATH="${TARGET_ABSOLUTE#"$REPO_ROOT"/}"
    INNER_PATH="${RELATIVE_PATH#ExternalAssets/}"
    [[ "$INNER_PATH" == */* ]] || fail "Utilisez ExternalAssets/<Discipline>/<AssetId>, pas un dossier global."

    dvc add "$RELATIVE_PATH"
    printf '\nLot indexé: %s\n' "$RELATIVE_PATH"
    printf 'Étapes suivantes: mettre à jour le registre, lancer assets-macos.sh push, puis committer les pointeurs.\n\n'
    git status --short -- "${RELATIVE_PATH}.dvc" "$(dirname -- "$RELATIVE_PATH")/.gitignore" docs/assets/ASSET_REGISTER.md
    ;;

  smoke-init)
    require_remote
    SMOKE_RELATIVE="ExternalAssets/Operations/VAULT-SMOKE-001"
    mkdir -p "$REPO_ROOT/$SMOKE_RELATIVE"
    printf 'GAME asset vault smoke test v1\n' > "$REPO_ROOT/$SMOKE_RELATIVE/proof.txt"
    dvc add "$SMOKE_RELATIVE"
    dvc push --remote "$REMOTE_NAME" "${SMOKE_RELATIVE}.dvc"
    printf 'Test envoyé. Committez le pointeur et le .gitignore généré dans une PR dédiée:\n'
    git status --short -- "${SMOKE_RELATIVE}.dvc" "$(dirname -- "$SMOKE_RELATIVE")/.gitignore"
    ;;

  smoke-verify)
    require_remote
    SMOKE_RELATIVE="ExternalAssets/Operations/VAULT-SMOKE-001"
    [[ -f "${SMOKE_RELATIVE}.dvc" ]] || fail "Le pointeur du test n'est pas encore présent dans Git. Faites d'abord git pull."
    dvc pull --remote "$REMOTE_NAME" "${SMOKE_RELATIVE}.dvc"
    SMOKE_CONTENT="$(sed -n '1p' "$SMOKE_RELATIVE/proof.txt" 2>/dev/null || true)"
    [[ "$SMOKE_CONTENT" == "GAME asset vault smoke test v1" ]] || fail "Le contenu restauré ne correspond pas à la preuve attendue."
    printf 'Restauration DVC vérifiée: %s/proof.txt\n' "$SMOKE_RELATIVE"
    ;;

  status)
    printf 'DVC %s\n' "$(dvc --version)"
    dvc status
    if remote_is_configured; then
      printf '\nComparaison avec le remote:\n'
      dvc status --cloud --remote "$REMOTE_NAME"
    else
      printf "\nRemote '%s' non configuré sur cette machine.\n" "$REMOTE_NAME"
    fi
    ;;

  help|-h|--help)
    usage
    ;;

  *)
    usage >&2
    fail "Action inconnue: $ACTION"
    ;;
esac
