from uuid import uuid4

import pytest

from app.core.enums import EnrichStatus
from app.core.exceptions import RateLimitExceeded
from app.infrastructure.protocols import FetchResult
from app.repositories.protocols import DomainCacheEntry
from app.schemas.company_profile import CompanyProfile
from app.schemas.lead_enriched import LeadQualification
from app.schemas.lead_in import LeadIn
from unittest.mock import AsyncMock


@pytest.mark.asyncio
class TestEnrichmentService:
    async def test_successful_enrichment(self, enrichment_service, sample_lead):
        result = await enrichment_service.enrich(sample_lead)
        assert result.enrich_status == EnrichStatus.OK
        assert result.domain == "logistics-de.ru"
        assert result.company_profile.company_name == "Logistics DE"
        assert result.lead_qualification.tier in ("warm", "hot")
        assert result.cached is False
        assert result.latency_ms >= 0

    async def test_no_domain_fails(self, enrichment_service):
        lead = LeadIn(name="Test", phone="+79991234567", email="user@gmail.com")
        result = await enrichment_service.enrich(lead)
        assert result.enrich_status == EnrichStatus.FAILED
        assert result.enrich_error == "no_domain"
        assert "enrich_failed" in result.crm_payload.tags

    async def test_idempotency_returns_same_response(self, enrichment_service, sample_lead):
        request_id = uuid4()
        lead = sample_lead.model_copy(update={"request_id": request_id})
        first = await enrichment_service.enrich(lead)
        second = await enrichment_service.enrich(lead)
        assert first.model_dump() == second.model_dump()

    async def test_domain_cache_second_request(self, enrichment_service, sample_lead):
        first = await enrichment_service.enrich(sample_lead.model_copy(update={"request_id": uuid4()}))
        second = await enrichment_service.enrich(
            sample_lead.model_copy(update={"request_id": uuid4()}),
        )
        assert first.cached is False
        assert second.cached is True
        assert second.company_profile.company_name == first.company_profile.company_name

    async def test_rate_limit_blocks_rapid_requests(self, enrichment_service, sample_lead, memory_repo):
        await enrichment_service.enrich(sample_lead.model_copy(update={"request_id": uuid4()}))
        memory_repo.domain_cache.clear()
        with pytest.raises(RateLimitExceeded):
            await enrichment_service.enrich(sample_lead.model_copy(update={"request_id": uuid4()}))

    async def test_site_unreachable(self, enrichment_service, memory_repo, mock_profile_extractor):
        fetcher = AsyncMock()
        fetcher.fetch = AsyncMock(
            return_value=FetchResult("", "https://unreachable.io", False, "site_unreachable"),
        )
        enrichment_service._fetcher = fetcher
        lead = LeadIn(
            name="Test",
            phone="+79991234567",
            email="user@unreachable.io",
            website="https://unreachable.io",
        )
        result = await enrichment_service.enrich(lead)
        assert result.enrich_status == EnrichStatus.FAILED
        assert result.enrich_error == "site_unreachable"

    async def test_partial_enrichment_on_llm_error(
        self, enrichment_service, sample_lead, logistics_profile,
    ):
        enrichment_service._profile_extractor.extract = AsyncMock(
            return_value=(logistics_profile, "ollama_unavailable"),
        )
        result = await enrichment_service.enrich(sample_lead)
        assert result.enrich_status == EnrichStatus.PARTIAL
        assert result.enrich_error == "ollama_unavailable"
        assert result.company_profile is not None

    async def test_audit_log_written(self, enrichment_service, sample_lead, memory_repo):
        await enrichment_service.enrich(sample_lead)
        assert len(memory_repo.audit_log) == 1
        assert memory_repo.audit_log[0]["enrich_status"] == EnrichStatus.OK

    async def test_build_from_cache_uses_lead_specific_crm(
        self, enrichment_service, sample_lead, memory_repo, logistics_profile,
    ):
        memory_repo.save_domain_cache(
            "logistics-de.ru",
            DomainCacheEntry(
                enrich_status=EnrichStatus.OK,
                company_profile=logistics_profile.model_dump(),
                lead_qualification=LeadQualification(tier="warm", lead_score=60).model_dump(),
                sources=["https://logistics-de.ru"],
            ),
        )
        lead = sample_lead.model_copy(update={"name": "Пётр", "request_id": uuid4()})
        result = await enrichment_service.enrich(lead)
        assert result.cached is True
        assert "Пётр" in result.crm_payload.name
