#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-status}"
PEER_ADDRESS="${2:-}"

find_tailscale_cli() {
  local candidate

  if [[ -n "${GAME_TAILSCALE_CLI:-}" && -x "${GAME_TAILSCALE_CLI}" ]]; then
    printf '%s\n' "$GAME_TAILSCALE_CLI"
    return 0
  fi

  for candidate in \
    "/Applications/Tailscale.app/Contents/MacOS/Tailscale" \
    "/Applications/Tailscale.localized/Tailscale.app/Contents/MacOS/Tailscale"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  if command -v tailscale >/dev/null 2>&1; then
    command -v tailscale
    return 0
  fi

  return 1
}

fail() {
  printf 'Erreur Tailscale: %s\n' "$1" >&2
  exit 1
}

TAILSCALE_CLI="$(find_tailscale_cli)" || fail "application absente. Relancez setup-macos.sh --remote-play."
STATUS_JSON="$("$TAILSCALE_CLI" status --json 2>/dev/null || true)"
BACKEND_STATE="$(printf '%s\n' "$STATUS_JSON" | sed -n 's/^[[:space:]]*"BackendState":[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"

if [[ "$BACKEND_STATE" != "Running" ]]; then
  fail "client non connecté (état: ${BACKEND_STATE:-inconnu}). Ouvrez Tailscale et rejoignez le tailnet de l'équipe."
fi

case "$ACTION" in
  status)
    TAILSCALE_IP="$("$TAILSCALE_CLI" ip -4 2>/dev/null | head -n 1)"
    [[ -n "$TAILSCALE_IP" ]] || fail "aucune IPv4 Tailscale attribuée."
    printf 'Tailscale connecté: %s\n' "$TAILSCALE_IP"
    ;;
  ip)
    TAILSCALE_IP="$("$TAILSCALE_CLI" ip -4 2>/dev/null | head -n 1)"
    [[ -n "$TAILSCALE_IP" ]] || fail "aucune IPv4 Tailscale attribuée."
    printf '%s\n' "$TAILSCALE_IP"
    ;;
  ping)
    [[ -n "$PEER_ADDRESS" ]] || fail "l'action ping attend l'IP Tailscale de l'hôte."
    "$TAILSCALE_CLI" ping --c 1 --until-direct=false --timeout 5s "$PEER_ADDRESS"
    ;;
  *)
    fail "action inconnue '$ACTION' (status, ip ou ping)."
    ;;
esac
