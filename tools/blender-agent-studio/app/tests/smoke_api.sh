#!/bin/zsh
set -euo pipefail

BASE="${BLENDER_STUDIO_URL:-http://127.0.0.1:8778}"
curl -fsS "$BASE/api/health" >/dev/null
curl -fsS "$BASE/" | grep -q '<title>Blender Team Studio</title>'
for endpoint in summary projects assets blender-assets tutorials runs workflows jobs docs mcp/status native-config; do
  curl -fsS "$BASE/api/$endpoint" >/dev/null
done
connected="$(curl -fsS "$BASE/api/mcp/status" | python3 -c 'import json,sys; print(str(json.load(sys.stdin)["connected"]).lower())')"
if [[ "${REQUIRE_MCP:-0}" == "1" ]]; then
  [[ "$connected" == "true" ]]
fi
echo "API et UI: OK · MCP connecté=$connected"
