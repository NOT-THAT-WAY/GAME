#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROLE="${1:-}"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/remote-test-macos.sh host [--name NAME] [--port 7770] [--skip-build]
  ./scripts/remote-test-macos.sh client --address TAILSCALE_HOST_IP [--name NAME] [--port 7770] [--skip-build]
EOF
}

[[ -n "$ROLE" ]] || { usage; exit 2; }
ROLE="$(printf '%s' "$ROLE" | tr '[:upper:]' '[:lower:]')"
[[ "$ROLE" == "host" || "$ROLE" == "client" ]] || { usage; exit 2; }
shift

FORWARD_ARGUMENTS=("$@")
HOST_ADDRESS=""
for (( index=0; index < ${#FORWARD_ARGUMENTS[@]}; index++ )); do
  if [[ "${FORWARD_ARGUMENTS[$index]}" == "--address" ]] && (( index + 1 < ${#FORWARD_ARGUMENTS[@]} )); then
    HOST_ADDRESS="${FORWARD_ARGUMENTS[$((index + 1))]}"
    break
  fi
done

LOCAL_TAILSCALE_IP="$($SCRIPT_DIR/tailscale-macos.sh ip)"

if [[ "$ROLE" == "host" ]]; then
  printf 'Adresse distante de l’hôte: %s (à partager uniquement avec l’équipe)\n' "$LOCAL_TAILSCALE_IP"
else
  [[ -n "$HOST_ADDRESS" ]] || { printf 'Erreur: le client attend --address TAILSCALE_HOST_IP.\n' >&2; exit 1; }
  printf 'Vérification Tailscale de l’hôte %s...\n' "$HOST_ADDRESS"
  "$SCRIPT_DIR/tailscale-macos.sh" ping "$HOST_ADDRESS"
fi

exec "$SCRIPT_DIR/first-test-macos.sh" "$ROLE" "${FORWARD_ARGUMENTS[@]}"
