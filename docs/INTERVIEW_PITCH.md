# Interview Pitch

## 30 секунд (elevator)

> В digital-агентстве менеджеры тратили по 15 минут на каждый лид — гуглили компанию по email и заполняли CRM вручную. Я собрал pipeline: форма → n8n → FastAPI-сервис, который сам скачивает сайт, через локальную LLM вытаскивает профиль компании и считает lead score. В CRM уходит один create уже с тегами hot/warm и summary. Hot-лиды могут улетать в Telegram. Экономия — часы в день при 50+ заявках.

## 2 минуты (technical deep-dive)

**Архитектура:** Variant B — enrich до create в CRM. Пользователь формы получает OK сразу; n8n асинхронно вызывает `/enrich-lead`.

**Domain resolve:** берём домен из корпоративного email или поля website; gmail/yandex отсекаем.

**Fetch + extract:** httpx с timeout, trafilatura для чистого текста. LLM **не ходит в интернет** — только парсит уже скачанный текст (~8k символов). Это убирает hallucinated URLs.

**LLM layer:** Ollama OpenAI-compatible API, `format: json`, Pydantic v2 validation. Если JSON битый — до 2 repair-ретраев с текстом ошибки в промпт. Если Ollama недоступен — rule-based fallback (industry по ключевым словам).

**Scoring:** rule-based: industry identified, enterprise hint, marketing keywords в comment, utm source. Пороги hot ≥80, warm ≥50 — конфигурируются.

**Production patterns:**
- Idempotency по `request_id` — безопасные retry n8n
- Postgres cache по domain, TTL 24h
- Audit log каждого enrich
- Graceful degrade: partial/failed → CRM create с тегом `enrich_failed`
- Rate limit 1 req/domain/min для demo

**Почему n8n:** оркестрация без деплоя кода — webhook, IF hot, CRM, Telegram, Postgres audit. Легко заменить mock CRM на AmoCRM v4 OAuth.

**Trade-offs:** без Playwright в MVP (флаг есть); без обхода anti-bot — осознанный scope для portfolio.

**Metrics для ROI:** latency_ms в ответе, audit table, tier distribution — можно строить dashboard.

## Вопросы, которые могут задать

| Вопрос | Ответ |
|---|---|
| Почему не Celery? | n8n уже оркестратор; для demo-volume достаточно sync enrich в HTTP node |
| Как боретесь с hallucinations? | LLM только на локальном тексте + Pydantic schema + repair retry |
| Idempotency? | `request_id` → stored full response in Postgres |
| Как подключить AmoCRM? | Заменить mock HTTP node; маппинг `crm_payload` → custom fields |
| CI без сети? | Fixture fetcher + mocked LLM in pytest |
