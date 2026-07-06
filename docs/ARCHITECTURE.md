# Architecture

## Layers

```
API (routes.py)
  └── Dependencies / DI container
        ├── EnrichmentService      ← business orchestration
        │     ├── DomainResolver   ← pure domain logic
        │     ├── LeadScorer
        │     ├── CrmPayloadBuilder
        │     └── Infrastructure adapters (fetcher, extractor, LLM)
        └── CrmService
              └── CrmRepository
```

## Component Diagram

```
┌─────────────┐     ┌──────────┐     ┌─────────────────┐     ┌──────────┐
│ demo form   │────▶│ n8n      │────▶│ lead-enricher   │────▶│ Postgres │
│ curl        │     │ WF-01    │     │ FastAPI :8080   │     │ cache    │
└─────────────┘     └────┬─────┘     └────────┬────────┘     │ audit    │
                         │                    │               │ crm_leads│
                         │                    ▼               └──────────┘
                         │             ┌──────────────┐
                         │             │ Ollama :11434│ (host)
                         │             └──────────────┘
                         ▼
                    ┌──────────┐
                    │ Mock CRM │
                    └──────────┘
```

## Enrichment Pipeline (EnrichmentService)

1. **Idempotency check** — `request_id` → stored response
2. **Domain resolve** — `DomainResolver` (corporate email or website)
3. **Cache lookup** — Postgres / in-memory, 24h TTL
4. **Rate limit** — 1 req/domain/60s (skipped on cache hit)
5. **Fetch** — `HttpxWebsiteFetcher` (fixtures for demo domains)
6. **Extract text** — `TrafilaturaTextExtractor`, max 8k chars
7. **LLM extraction** — `OllamaProfileExtractor` → Pydantic, repair retries
8. **Scoring** — `LeadScorer` (rules) → hot/warm/cold
9. **CRM payload** — `CrmPayloadBuilder`
10. **Persist** — cache + idempotency + audit log

## Testing Strategy

| Layer | Test file | DB required |
|---|---|---|
| Domain | `test_domain_resolve.py`, `test_scorer.py` | No |
| Service | `test_enrichment_service.py` | No (in-memory repo) |
| Infrastructure | `test_infrastructure.py`, `test_llm.py` | No |
| Repository | `test_repositories.py` | No |
| API | `test_api.py` | No (in-memory DI) |
| Live | `pytest -m live` | Postgres + Ollama |

## Failure Modes

| Error | Behavior |
|---|---|
| `no_domain` | failed; CRM payload with `enrich_failed` tag |
| `site_unreachable` | failed; fallback create in n8n |
| `ollama_unavailable` | partial; rule-based profile |
| `llm_invalid_json` | retry ×2, then partial with fallback |
| Rate limit | HTTP 429 |
