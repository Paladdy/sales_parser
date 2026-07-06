import logging
from typing import Optional
from uuid import UUID

from app.repositories.protocols import CrmRepository

logger = logging.getLogger(__name__)


class CrmService:
    def __init__(self, repository: CrmRepository) -> None:
        self._repo = repository

    def create_lead(
        self,
        name: str,
        phone: str,
        email: str,
        tags: list[str],
        custom_fields: dict,
        tier: Optional[str] = None,
        source_request_id: Optional[UUID] = None,
    ) -> int:
        lead_id = self._repo.create_lead(
            name=name,
            phone=phone,
            email=email,
            tags=tags,
            custom_fields=custom_fields,
            tier=tier,
            source_request_id=source_request_id,
        )
        logger.info("CRM lead created id=%s name=%s", lead_id, name)
        return lead_id
