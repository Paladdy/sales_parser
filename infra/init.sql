CREATE TABLE IF NOT EXISTS domain_enrichment_cache (
    domain VARCHAR(255) PRIMARY KEY,
    payload JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_domain_cache_expires ON domain_enrichment_cache (expires_at);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    request_id UUID PRIMARY KEY,
    response JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS enrichment_audit (
    id SERIAL PRIMARY KEY,
    request_id UUID NOT NULL,
    domain VARCHAR(255),
    enrich_status VARCHAR(32) NOT NULL,
    tier VARCHAR(32),
    lead_score INTEGER,
    cached BOOLEAN DEFAULT FALSE,
    latency_ms INTEGER,
    error_code VARCHAR(512),
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_request_id ON enrichment_audit (request_id);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON enrichment_audit (created_at DESC);

CREATE TABLE IF NOT EXISTS crm_leads (
    id SERIAL PRIMARY KEY,
    name VARCHAR(512) NOT NULL,
    phone VARCHAR(64),
    email VARCHAR(255),
    tags JSONB DEFAULT '[]',
    custom_fields JSONB DEFAULT '{}',
    tier VARCHAR(32),
    source_request_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS domain_rate_limit (
    domain VARCHAR(255) PRIMARY KEY,
    last_request_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
