#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  set -a && source "$ROOT/.env" && set +a
fi

POSTGRES_HOST_PORT="${POSTGRES_HOST_PORT:-55433}"
ENRICHER_HOST_PORT="${ENRICHER_HOST_PORT:-18080}"
N8N_HOST_PORT="${N8N_HOST_PORT:-15678}"

WEBHOOK_URL="${N8N_WEBHOOK_URL:-http://localhost:${N8N_HOST_PORT}/webhook/new-lead}"
ENRICH_URL="${ENRICH_URL:-http://localhost:${ENRICHER_HOST_PORT}/enrich-lead}"
PG_URL="${DATABASE_URL_HOST:-postgresql://lead:lead@localhost:${POSTGRES_HOST_PORT}/lead_enricher}"

echo "=== 1. Health check ==="
curl -sf "http://localhost:${ENRICHER_HOST_PORT}/health" | python3 -m json.tool

echo ""
echo "=== 2. Direct enrich (fixture domain) ==="
REQUEST_ID="$(uuidgen 2>/dev/null || echo '00000000-0000-0000-0000-000000000001')"
RESP=$(curl -s -X POST "$ENRICH_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"request_id\": \"${REQUEST_ID}\",
    \"name\": \"Иван\",
    \"phone\": \"+79991234567\",
    \"email\": \"ivan@logistics-de.ru\",
    \"comment\": \"Нужна реклама для логистической компании\",
    \"utm_source\": \"yandex\"
  }")
echo "$RESP" | python3 -m json.tool

if echo "$RESP" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
  TIER=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('lead_qualification',{}).get('tier','N/A'))")
  COMPANY=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('company_profile',{}).get('company_name','N/A'))")
  STATUS=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('enrich_status','unknown'))")
else
  TIER="N/A"
  COMPANY="N/A"
  STATUS="error"
fi

echo ""
echo "=== 3. n8n webhook (if n8n is running) ==="
if curl -sf -o /dev/null -w "%{http_code}" -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo","phone":"+7999","email":"ivan@logistics-de.ru","comment":"test"}' | grep -qE '200|201'; then
  echo "Webhook accepted. Waiting 5s..."
  sleep 5
else
  echo "n8n webhook not available — skip (import WF-01-lead-enrichment.json first)"
fi

echo ""
echo "=== 4. Mock CRM leads (Postgres) ==="
if command -v psql &>/dev/null; then
  psql "$PG_URL" -c "SELECT id, name, tier, created_at FROM crm_leads ORDER BY id DESC LIMIT 3;" 2>/dev/null || \
    echo "Postgres not reachable at $PG_URL"
else
  echo "psql not installed — query crm_leads manually"
fi

echo ""
echo "=== Result ==="
echo "Status: $STATUS"
echo "Tier: $TIER"
echo "Company: $COMPANY"
