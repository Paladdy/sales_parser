#!/usr/bin/env bash
# Full end-to-end smoke test for sales_parser.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then set -a && source .env && set +a; fi
ENRICHER_PORT="${ENRICHER_HOST_PORT:-18080}"
N8N_PORT="${N8N_HOST_PORT:-15678}"

pass=0
fail=0

check() {
  local name="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "PASS  $name"
    pass=$((pass + 1))
  else
    echo "FAIL  $name"
    fail=$((fail + 1))
  fi
}

echo "=== sales_parser E2E check ==="
echo ""

check "docker stack running" docker compose ps --status running -q
check "API health" curl -sf "http://localhost:${ENRICHER_PORT}/health"
check "n8n UI" curl -sf -o /dev/null "http://localhost:${N8N_PORT}/"

REQ=$(uuidgen 2>/dev/null || echo "00000000-0000-0000-0000-000000000099")
ENRICH=$(curl -s -X POST "http://localhost:${ENRICHER_PORT}/enrich-lead" \
  -H "Content-Type: application/json" \
  -d "{\"request_id\":\"${REQ}\",\"name\":\"Test\",\"phone\":\"+79991234567\",\"email\":\"ivan@logistics-de.ru\",\"comment\":\"test\",\"utm_source\":\"yandex\"}")

STATUS=$(echo "$ENRICH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('enrich_status',''))" 2>/dev/null || echo "")
if [[ "$STATUS" == "ok" || "$STATUS" == "partial" ]]; then
  echo "PASS  enrich-lead (status=$STATUS)"
  pass=$((pass + 1))
else
  echo "FAIL  enrich-lead (status=$STATUS)"
  fail=$((fail + 1))
fi

WEBHOOK_HTTP=$(curl -s -o /tmp/e2e-webhook.json -w "%{http_code}" -X POST \
  "http://localhost:${N8N_PORT}/webhook/new-lead" \
  -H "Content-Type: application/json" \
  -d '{"name":"E2E","phone":"+79991234567","email":"ivan@logistics-de.ru","comment":"test"}')

if [[ "$WEBHOOK_HTTP" == "200" ]]; then
  echo "PASS  n8n webhook (HTTP 200)"
  pass=$((pass + 1))
else
  echo "FAIL  n8n webhook (HTTP $WEBHOOK_HTTP) — run: make import-workflow"
  fail=$((fail + 1))
fi

if [[ -x services/lead-enricher/.venv/bin/python ]]; then
  if services/lead-enricher/.venv/bin/python -m pytest services/lead-enricher/tests/ -q --tb=line 2>&1 | grep -q "passed"; then
    echo "PASS  unit tests"
    pass=$((pass + 1))
  else
    echo "FAIL  unit tests"
    fail=$((fail + 1))
  fi
else
  echo "SKIP  unit tests (no .venv)"
fi

echo ""
echo "=== $pass passed, $fail failed ==="
[[ "$fail" -eq 0 ]]
