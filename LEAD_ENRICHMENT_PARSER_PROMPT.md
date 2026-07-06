# Prompt: pet-project «Lead Enrichment Parser» для портфолио

> Скопируй **весь файл** в новый чат (Agent mode).  
> Путь для проекта: `~/lead-enrichment-parser`  
> Ollama уже запущен локально на `:11434`.

---

## Контекст автора (background для архитектурных решений)

Я — Python backend / AI automation engineer (~4 года). Стек и паттерны, которые нужно переиспользовать:

- **FastAPI** — микросервисы, REST API, Pydantic v2
- **n8n** — оркестрация workflow (webhook → HTTP → IF → CRM/Telegram)
- **LLM** — Ollama (OpenAI-compatible API), structured JSON output, prompt engineering
- **PostgreSQL** — кэш, dedup, audit log
- **Docker Compose** — локальный demo-стенд
- **Паттерны production:** idempotency, retry, fallback, human-in-the-loop, DLQ-lite (лог failed enrich)

Опыт: digital-агентство (CRM AmoCRM/Bitrix, lead routing), Support RAG (pgvector), webhook-gateway (HMAC, idempotency).

**Цель проекта:** портфолио-кейс для вакансий AI Engineer / LLM Developer / n8n automation.  
Не tutorial «hello scraper», а **production-minded demo** с измеримым бизнес-ROI.

**Бизнес-история (для README):**  
В digital-агентстве менеджеры получали лиды с лендинга (имя, телефон, email) и вручную гуглили компанию по domain/email — 15–20 мин на лид. Мы автоматизировали: форма → n8n → enrichment parser → один create в CRM уже с company profile и lead score → hot leads в Telegram.

---

## Архитектура (Вариант B — enrich ПЕРЕД create в CRM)

```
[Landing Form / demo HTML / curl]
        │ POST webhook (raw lead)
        ▼
[n8n WF-01 Lead Intake]
        │ POST /enrich-lead
        ▼
[FastAPI lead-enricher]
   1. resolve domain from email (ivan@logistics-de.ru → logistics-de.ru)
   2. Playwright or httpx fetch homepage (+ optional /about, /contacts)
   3. HTML → clean text (readability / trafilatura / bs4)
   4. LLM structured extraction → Pydantic schema
   5. rule-based + LLM lead scoring (hot/warm/cold)
   6. cache by domain in Postgres (24h TTL)
   7. return enriched payload + confidence + tier
        │
        ▼
[n8n WF-01 continued]
   IF enrich_ok → AmoCRM create (or mock CRM API)
   IF enrich_failed → fallback create with tag enrich_failed
   IF tier == hot → Telegram notify manager
   Log to Postgres audit table
```

**Важно:**

- Лид создаётся в CRM **ОДИН РАЗ** (не create → update)
- LLM **НЕ ходит на сайт** — только парсит уже скачанный текст
- Форма отвечает пользователю сразу «OK»; enrich асинхронно в n8n

---

## Scope MVP (что обязательно сделать)

### 1. Repo: `lead-enrichment-parser/` (новый проект)

```
lead-enrichment-parser/
├── README.md
├── docker-compose.yml
├── .env.example
├── Makefile
├── services/
│   └── lead-enricher/
│       ├── app/
│       │   ├── main.py
│       │   ├── config.py
│       │   ├── schemas/
│       │   │   ├── lead_in.py
│       │   │   ├── lead_enriched.py
│       │   │   └── company_profile.py
│       │   ├── fetcher/       # httpx + optional Playwright
│       │   ├── extractor/     # html → text
│       │   ├── llm/           # Ollama client, structured output, repair retry
│       │   ├── scorer.py
│       │   ├── cache.py
│       │   └── db.py
│       ├── tests/
│       │   ├── test_domain_resolve.py
│       │   ├── test_scorer.py
│       │   └── fixtures/      # saved HTML snippets
│       ├── Dockerfile
│       └── requirements.txt
├── workflows/
│   └── export/
│       └── WF-01-lead-enrichment.json
├── demo/
│   ├── index.html
│   ├── sample_leads.json
│   └── demo.sh
├── infra/
│   └── init.sql
└── docs/
    ├── ARCHITECTURE.md
    ├── API.md
    └── INTERVIEW_PITCH.md
```

### 2. FastAPI service: `lead-enricher`

**Endpoints:**

`GET /health` → `{ "status": "ok" }`

`POST /enrich-lead`

Request:

```json
{
  "request_id": "uuid",
  "name": "Иван",
  "phone": "+79991234567",
  "email": "ivan@logistics-de.ru",
  "website": "https://logistics-de.ru",
  "comment": "Нужна реклама для логистической компании",
  "utm_source": "yandex"
}
```

Response (success):

```json
{
  "request_id": "uuid",
  "enrich_status": "ok",
  "domain": "logistics-de.ru",
  "company_profile": {
    "company_name": "Logistics DE",
    "industry": "logistics",
    "services": ["freight", "warehousing"],
    "city": "Hamburg",
    "company_size_hint": "sme",
    "summary": "..."
  },
  "lead_qualification": {
    "is_lpr_likely": false,
    "signals": ["comment mentions marketing need"],
    "lead_score": 72,
    "tier": "warm",
    "confidence": 0.81
  },
  "crm_payload": {
    "name": "Иван — Logistics DE",
    "phone": "+79991234567",
    "email": "ivan@logistics-de.ru",
    "tags": ["enriched", "from_yandex", "tier_warm"],
    "custom_fields": {}
  },
  "sources": ["https://logistics-de.ru"],
  "cached": false,
  "latency_ms": 4200
}
```

Response (partial/fail):

```json
{
  "request_id": "uuid",
  "enrich_status": "partial|failed",
  "enrich_error": "site_unreachable|llm_invalid_json|no_domain",
  "crm_payload": {},
  "lead_qualification": { "tier": "unknown", "lead_score": 0 }
}
```

**Логика:**

- Domain resolve: email domain (skip gmail.com, yandex.ru, mail.ru) OR explicit website field
- Fetch: httpx first; Playwright fallback if empty/JS-heavy (config flag)
- Text limit: max ~8k chars for LLM
- LLM: Ollama `llama3.2`; temperature 0.1; JSON-only output
- Pydantic validate → up to 2 repair retries with error feedback to LLM
- Scoring: rules + optional LLM tier
- Cache: Postgres `domain_enrichment_cache(domain, payload, expires_at)`
- Idempotency: same `request_id` → same response
- Rate limit: 1 req/domain/60s for demo

**Env vars (.env.example):**

```
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2
DATABASE_URL=postgresql://lead:lead@postgres:5432/lead_enricher
FETCH_TIMEOUT_SEC=15
USE_PLAYWRIGHT=false
HOT_SCORE_THRESHOLD=80
WARM_SCORE_THRESHOLD=50
N8N_WEBHOOK_URL=http://localhost:5678/webhook/new-lead
TELEGRAM_BOT_TOKEN=
TELEGRAM_MANAGER_CHAT_ID=
```

### 3. n8n workflow `WF-01 Lead Enrichment`

Nodes:

1. **Webhook** `POST /webhook/new-lead`
2. **Set** — generate `request_id` if missing
3. **HTTP Request** → `POST http://lead-enricher:8080/enrich-lead`
4. **IF** enrich_status != failed (always continue with fallback payload)
5. **HTTP Request** → Mock CRM `POST /mock-crm/leads`
6. **IF** tier == hot → **Telegram** sendMessage
7. **Postgres** insert audit row
8. **Respond to Webhook** → `{ "ok": true }`

Export JSON в `workflows/export/`.

### 4. Mock CRM

`POST /mock-crm/leads` — пишет в Postgres `crm_leads`, возвращает `{ "lead_id": 123 }`.  
В README — секция «как подключить AmoCRM v4 API».

### 5. Demo landing form

`demo/index.html` — name, phone, email, comment, website (optional).  
Submit → n8n webhook. Success message сразу, не ждать enrich.

### 6. Docker Compose

Services: `postgres`, `lead-enricher` (:8080), `n8n` (:5678).  
Ollama **не в compose** — host `:11434`, `host.docker.internal`.

Commands: `make up`, `make demo`, `make test`.

### 7. Tests

- Unit: domain resolve, free email detection, scorer thresholds
- Integration: enrich with fixture HTML (mock fetcher, no network in CI)
- Optional live test: `pytest -m live` (skipped by default)

### 8. README

1. Problem — manual lead research 15–20 min
2. Solution — mermaid diagram
3. ROI — «50 leads/day × 15 min = 12.5h saved»
4. Quick start
5. Architecture decisions
6. Interview pitch (30 sec)

### 9. docs/INTERVIEW_PITCH.md

Готовый текст на русском: 30 сек + технический deep-dive 2 мин.

---

## Non-goals (НЕ делать)

- Не обходить CAPTCHA, login walls, anti-bot
- Не scrape social media
- Не «универсальный scraper 1000 сайтов»
- Не over-engineer: без Kubernetes, Celery
- Не fine-tune моделей
- Не AmoCRM OAuth в MVP (mock + docs)
- Не лишние markdown файлы кроме перечисленных

---

## Качество кода

- Python 3.11+, type hints, Pydantic v2
- Простой production FastAPI
- Comments только для non-obvious logic
- Structured errors, logging with request_id

---

## Demo script (`demo/demo.sh`)

```bash
#!/usr/bin/env bash
# 1. health check
# 2. POST sample lead to n8n webhook
# 3. wait 5s
# 4. query Postgres / mock CRM
# 5. print tier + company_profile
```

---

## Definition of Done

- [ ] `docker compose up` поднимает postgres + enricher + n8n
- [ ] demo form или curl — enriched lead end-to-end
- [ ] Ollama extraction работает; graceful degrade if Ollama down
- [ ] Domain cache (second request → cached: true)
- [ ] Idempotency by request_id
- [ ] n8n workflow exported and importable
- [ ] Tests pass
- [ ] README с ROI понятен рекрутеру

---

## Порядок реализации

1. Scaffold repo + docker-compose + postgres schema
2. FastAPI `/enrich-lead` with mocked fetcher + fixture HTML
3. Ollama LLM extraction + Pydantic + retry
4. Scorer + crm_payload builder
5. Cache + idempotency
6. Real httpx fetcher
7. n8n workflow + mock CRM
8. demo/index.html + demo.sh
9. Tests + README + INTERVIEW_PITCH.md

---

## Demo fixtures

3 локальных HTML fixture (без flaky external network):

- logistics company page
- digital agency page
- minimal page (partial extraction)

Serve at `/fixtures/company-a.html` или из `tests/fixtures/`.

---

## Telegram (optional)

If `TELEGRAM_BOT_TOKEN` + `TELEGRAM_MANAGER_CHAT_ID` set — hot alert.  
If not — skip gracefully.

---

## Output expected from AI

1. Create full project structure with working code
2. Exact commands to run demo locally
3. Manual steps (import n8n workflow, webhook URL in demo form)
4. Sensible defaults documented in README

**Start by scaffolding repo and FastAPI enricher with fixture-based fetcher first, then wire n8n.**  
**Do NOT ask clarifying questions unless blocked.**
