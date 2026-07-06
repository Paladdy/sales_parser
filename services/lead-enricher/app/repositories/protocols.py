from dataclasses import dataclass
from typing import Any, Optional, Protocol
from uuid import UUID


@dataclass(frozen=True)
class DomainCacheEntry:
    enrich_status: str
    company_profile: dict[str, Any] | None
    lead_qualification: dict[str, Any]
    sources: list[str]


class EnrichmentRepository(Protocol):
    def get_idempotent(self, request_id: UUID) -> Optional[dict[str, Any]]: ...

    def save_idempotent(self, request_id: UUID, response: dict[str, Any]) -> None: ...

    def get_domain_cache(self, domain: str) -> Optional[DomainCacheEntry]: ...

    def save_domain_cache(self, domain: str, entry: DomainCacheEntry) -> None: ...

    def check_rate_limit(self, domain: str, window_sec: int = 60) -> bool: ...

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
    ) -> None: ...


class CrmRepository(Protocol):
    def create_lead(
        self,
        name: str,
        phone: str,
        email: str,
        tags: list[str],
        custom_fields: dict,
        tier: Optional[str],
        source_request_id: Optional[UUID],
    ) -> int: ...
