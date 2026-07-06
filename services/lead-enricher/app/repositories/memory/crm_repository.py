from typing import Optional
from uuid import UUID

from app.repositories.memory.enrichment_repository import InMemoryEnrichmentRepository


class InMemoryCrmRepository:
    def __init__(self) -> None:
        self.leads: list[dict] = []
        self._next_id = 1

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
        lead_id = self._next_id
        self._next_id += 1
        self.leads.append({
            "id": lead_id,
            "name": name,
            "phone": phone,
            "email": email,
            "tags": tags,
            "custom_fields": custom_fields,
            "tier": tier,
            "source_request_id": str(source_request_id) if source_request_id else None,
        })
        return lead_id
