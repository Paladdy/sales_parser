import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from app.repositories.protocols import DomainCacheEntry, EnrichmentRepository

logger = logging.getLogger(__name__)


class InMemoryEnrichmentRepository:
    """In-memory repository for unit tests and offline development."""

    def __init__(self) -> None:
        self.idempotency: dict[str, dict[str, Any]] = {}
        self.domain_cache: dict[str, tuple[DomainCacheEntry, datetime]] = {}
        self.rate_limits: dict[str, datetime] = {}
        self.audit_log: list[dict[str, Any]] = []

    def get_idempotent(self, request_id: UUID) -> Optional[dict[str, Any]]:
        return self.idempotency.get(str(request_id))

    def save_idempotent(self, request_id: UUID, response: dict[str, Any]) -> None:
        self.idempotency.setdefault(str(request_id), response)

    def get_domain_cache(self, domain: str) -> Optional[DomainCacheEntry]:
        row = self.domain_cache.get(domain)
        if not row:
            return None
        entry, expires_at = row
        if expires_at <= datetime.now(timezone.utc):
            del self.domain_cache[domain]
            return None
        return entry

    def save_domain_cache(self, domain: str, entry: DomainCacheEntry) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        self.domain_cache[domain] = (entry, expires_at)

    def check_rate_limit(self, domain: str, window_sec: int = 60) -> bool:
        now = datetime.now(timezone.utc)
        last = self.rate_limits.get(domain)
        if last and last > now - timedelta(seconds=window_sec):
            return False
        self.rate_limits[domain] = now
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
        self.audit_log.append({
            "request_id": str(request_id),
            "domain": domain,
            "enrich_status": enrich_status,
            "tier": tier,
            "lead_score": lead_score,
            "cached": cached,
            "latency_ms": latency_ms,
            "error_code": error_code,
            "payload": payload,
        })

    def ping(self) -> bool:
        return True
