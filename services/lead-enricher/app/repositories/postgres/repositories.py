import json
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings
from app.repositories.protocols import DomainCacheEntry, EnrichmentRepository

logger = logging.getLogger(__name__)


class PostgresEnrichmentRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or settings.database_url
        self._pool: ConnectionPool | None = None

    def open(self) -> None:
        if self._pool is not None:
            return
        self._pool = ConnectionPool(
            conninfo=self._database_url,
            min_size=1,
            max_size=10,
            open=True,
            kwargs={"row_factory": dict_row},
        )

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool = None

    @contextmanager
    def _conn(self):
        if self._pool is None:
            self.open()
        assert self._pool is not None
        with self._pool.connection() as conn:
            yield conn

    def ping(self) -> bool:
        try:
            with self._conn() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as exc:
            logger.warning("Database ping failed: %s", exc)
            return False

    def get_idempotent(self, request_id: UUID) -> Optional[dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT response FROM idempotency_keys WHERE request_id = %s",
                (str(request_id),),
            ).fetchone()
        if not row:
            return None
        payload = row["response"]
        if isinstance(payload, str):
            return json.loads(payload)
        return payload

    def save_idempotent(self, request_id: UUID, response: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO idempotency_keys (request_id, response)
                VALUES (%s, %s)
                ON CONFLICT (request_id) DO NOTHING
                """,
                (str(request_id), json.dumps(response)),
            )

    def get_domain_cache(self, domain: str) -> Optional[DomainCacheEntry]:
        now = datetime.now(timezone.utc)
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT payload FROM domain_enrichment_cache
                WHERE domain = %s AND expires_at > %s
                """,
                (domain, now),
            ).fetchone()
        if not row:
            return None
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return DomainCacheEntry(
            enrich_status=payload["enrich_status"],
            company_profile=payload.get("company_profile"),
            lead_qualification=payload["lead_qualification"],
            sources=payload.get("sources", []),
        )

    def save_domain_cache(self, domain: str, entry: DomainCacheEntry) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.cache_ttl_hours)
        payload = {
            "enrich_status": entry.enrich_status,
            "company_profile": entry.company_profile,
            "lead_qualification": entry.lead_qualification,
            "sources": entry.sources,
        }
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO domain_enrichment_cache (domain, payload, expires_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (domain) DO UPDATE
                SET payload = EXCLUDED.payload, expires_at = EXCLUDED.expires_at
                """,
                (domain, json.dumps(payload), expires_at),
            )

    def check_rate_limit(self, domain: str, window_sec: int = 60) -> bool:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window_sec)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT last_request_at FROM domain_rate_limit WHERE domain = %s",
                (domain,),
            ).fetchone()
            if row and row["last_request_at"] > cutoff:
                return False
            conn.execute(
                """
                INSERT INTO domain_rate_limit (domain, last_request_at)
                VALUES (%s, %s)
                ON CONFLICT (domain) DO UPDATE SET last_request_at = EXCLUDED.last_request_at
                """,
                (domain, now),
            )
        return True

    def log_audit(
        self,
        request_id: UUID,
        domain: Optional[str],
        enrich_status: str,
        tier: Optional[str],
        lead_score: Optional[int],
        cached: bool,
        latency_ms: int,
        error_code: Optional[str],
        payload: dict[str, Any],
    ) -> None:
        try:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO enrichment_audit
                        (request_id, domain, enrich_status, tier, lead_score,
                         cached, latency_ms, error_code, payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(request_id),
                        domain,
                        enrich_status,
                        tier,
                        lead_score,
                        cached,
                        latency_ms,
                        error_code,
                        json.dumps(payload),
                    ),
                )
        except Exception as exc:
            logger.warning("Failed to write audit log: %s", exc)


class PostgresCrmRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or settings.database_url
        self._pool: ConnectionPool | None = None

    def open(self) -> None:
        if self._pool is not None:
            return
        self._pool = ConnectionPool(
            conninfo=self._database_url,
            min_size=1,
            max_size=5,
            open=True,
            kwargs={"row_factory": dict_row},
        )

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool = None

    @contextmanager
    def _conn(self):
        if self._pool is None:
            self.open()
        assert self._pool is not None
        with self._pool.connection() as conn:
            yield conn

    def create_lead(
        self,
        name: str,
        phone: str,
        email: str,
        tags: list[str],
        custom_fields: dict,
        tier: Optional[str],
        source_request_id: Optional[UUID],
    ) -> int:
        with self._conn() as conn:
            row = conn.execute(
                """
                INSERT INTO crm_leads (name, phone, email, tags, custom_fields, tier, source_request_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    name,
                    phone,
                    email,
                    json.dumps(tags),
                    json.dumps(custom_fields),
                    tier,
                    str(source_request_id) if source_request_id else None,
                ),
            ).fetchone()
        return row["id"]
