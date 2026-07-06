#!/usr/bin/env bash
# Check whether sales_parser host ports are free before `make up`.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/.env"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a && source "$ENV_FILE" && set +a
fi

POSTGRES_HOST_PORT="${POSTGRES_HOST_PORT:-55433}"
ENRICHER_HOST_PORT="${ENRICHER_HOST_PORT:-18080}"
N8N_HOST_PORT="${N8N_HOST_PORT:-15678}"

check_port() {
  local port="$1" label="$2"
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    local proc
    proc=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | tail -1 | awk '{print $1, "(pid", $2")"}')
    echo "BUSY  $label → localhost:$port  ($proc)"
    return 1
  fi
  echo "OK    $label → localhost:$port"
  return 0
}

echo "sales_parser port check"
echo "-----------------------"
failed=0
check_port "$POSTGRES_HOST_PORT" "Postgres" || failed=1
check_port "$ENRICHER_HOST_PORT" "Lead Enricher API" || failed=1
check_port "$N8N_HOST_PORT" "n8n" || failed=1

echo ""
if [[ "$failed" -eq 1 ]]; then
  echo "Some ports are busy. Edit .env (POSTGRES_HOST_PORT, ENRICHER_HOST_PORT, N8N_HOST_PORT)"
  echo "and update N8N_WEBHOOK_URL / ENRICH_URL / DATABASE_URL_HOST to match."
  exit 1
fi
echo "All ports free."
