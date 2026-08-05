#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"
docker compose -f compose.yml up --build -d
open "http://127.0.0.1:8778"
