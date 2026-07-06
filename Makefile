.PHONY: up down logs test demo health enrich lint ports import-workflow

POSTGRES_HOST_PORT ?= 55433
ENRICHER_HOST_PORT ?= 18080
N8N_HOST_PORT      ?= 15678
ENRICH_URL         ?= http://localhost:$(ENRICHER_HOST_PORT)/enrich-lead

up: ports
	cp -n .env.example .env 2>/dev/null || true
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f lead-enricher

ports:
	@bash scripts/check-ports.sh

import-workflow:
	@bash scripts/import-n8n-workflow.sh

verify:
	@bash scripts/verify-e2e.sh

test:
	cd services/lead-enricher && .venv/bin/python -m pytest tests/ -v --tb=short

test-cov:
	cd services/lead-enricher && .venv/bin/python -m pytest tests/ -v --cov=app --cov-report=term-missing

test-live:
	cd services/lead-enricher && python -m pytest tests/ -v -m live

health:
	curl -s http://localhost:$(ENRICHER_HOST_PORT)/health | python3 -m json.tool

demo:
	bash demo/demo.sh

enrich:
	curl -s -X POST $(ENRICH_URL) \
		-H "Content-Type: application/json" \
		-d @demo/sample_leads.json | python3 -m json.tool

lint:
	cd services/lead-enricher && python -m ruff check app tests 2>/dev/null || true
