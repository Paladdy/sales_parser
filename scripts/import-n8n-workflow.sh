#!/usr/bin/env bash
# Import WF-01 into n8n via CLI and activate webhook.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

WORKFLOW_ID="7f3c8a2e-1b4d-4e9a-9c6f-2d8e5a1b3c7d"
N8N_PORT="${N8N_HOST_PORT:-15678}"

if ! docker compose ps n8n --status running -q 2>/dev/null | grep -q .; then
  echo "n8n is not running. Start stack first: make up"
  exit 1
fi

echo "Copying workflow into n8n container..."
docker compose cp workflows/export/WF-01-lead-enrichment.json n8n:/tmp/WF-01-lead-enrichment.json

echo "Importing workflow..."
docker compose exec -u node n8n n8n import:workflow --input=/tmp/WF-01-lead-enrichment.json

echo "Publishing workflow (activates webhook)..."
docker compose exec -u node n8n n8n publish:workflow --id="$WORKFLOW_ID" || \
  docker compose exec -u node n8n n8n update:workflow --id="$WORKFLOW_ID" --active=true

echo "Restarting n8n to register webhook..."
docker compose restart n8n
sleep 8

echo ""
echo "Testing webhook..."
HTTP=$(curl -s -o /tmp/n8n-webhook-test.json -w "%{http_code}" -X POST \
  "http://localhost:${N8N_PORT}/webhook/new-lead" \
  -H "Content-Type: application/json" \
  -d '{"name":"Import Test","phone":"+79991234567","email":"ivan@logistics-de.ru","comment":"test"}')

if [[ "$HTTP" == "200" ]]; then
  echo "Webhook OK (HTTP 200): $(cat /tmp/n8n-webhook-test.json)"
else
  echo "Webhook returned HTTP $HTTP — open http://localhost:${N8N_PORT} and toggle Active on WF-01"
  cat /tmp/n8n-webhook-test.json 2>/dev/null || true
fi

echo ""
echo "n8n UI: http://localhost:${N8N_PORT}"
echo "Webhook: http://localhost:${N8N_PORT}/webhook/new-lead"
