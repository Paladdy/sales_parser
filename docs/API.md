# API Reference

Base URL: `http://localhost:18080` (configurable via `ENRICHER_HOST_PORT` in `.env`)

## GET /health

```json
{ "status": "ok" }
```

## POST /enrich-lead

Enriches a lead with company profile and qualification.

### Request

| Field | Type | Required | Description |
|---|---|---|---|
| `request_id` | UUID | no | Idempotency key; generated if missing |
| `name` | string | yes | Contact name |
| `phone` | string | yes | Phone number |
| `email` | email | yes | Contact email |
| `website` | string | no | Company website (required for free email) |
| `comment` | string | no | Form comment |
| `utm_source` | string | no | Traffic source tag |

### Response (success)

| Field | Description |
|---|---|
| `enrich_status` | `ok`, `partial`, or `failed` |
| `domain` | Resolved company domain |
| `company_profile` | Extracted company data |
| `lead_qualification` | Score, tier, signals |
| `crm_payload` | Ready for CRM create |
| `cached` | Whether result came from domain cache |
| `latency_ms` | Processing time |

### Response (failure)

```json
{
  "request_id": "...",
  "enrich_status": "failed",
  "enrich_error": "no_domain|site_unreachable|llm_invalid_json",
  "crm_payload": { "tags": ["enrich_failed", ...] },
  "lead_qualification": { "tier": "unknown", "lead_score": 0 }
}
```

## POST /mock-crm/leads

Mock CRM endpoint for n8n workflow.

### Request

```json
{
  "name": "Иван — Logistics DE",
  "phone": "+79991234567",
  "email": "ivan@logistics-de.ru",
  "tags": ["enriched", "tier_warm"],
  "custom_fields": { "industry": "logistics" },
  "tier": "warm",
  "source_request_id": "uuid"
}
```

### Response

```json
{ "lead_id": 1 }
```

## GET /fixtures/{filename}

Serves HTML test fixtures (`logistics.html`, `agency.html`, `minimal.html`).

## Error Codes

| Code | Meaning |
|---|---|
| `no_domain` | Free email and no website |
| `site_unreachable` | HTTP fetch failed |
| `ollama_unavailable` | LLM down; fallback profile used |
| `llm_invalid_json` | JSON parse/validation failed after retries |
| `empty_text` | Page had insufficient text |
