import logging
import time
from typing import Optional
from uuid import UUID, uuid4

from app.core.enums import EnrichStatus
from app.core.exceptions import RateLimitExceeded
from app.domain.crm_builder import CrmPayloadBuilder
from app.domain.domain_resolver import DomainResolver
from app.domain.lead_scorer import LeadScorer
from app.infrastructure.protocols import (
    CompanyProfileExtractor,
    TextExtractor,
    WebsiteFetcher,
)
from app.repositories.protocols import DomainCacheEntry, EnrichmentRepository
from app.schemas.company_profile import CompanyProfile
from app.schemas.lead_enriched import CrmPayload, LeadEnriched, LeadQualification
from app.schemas.lead_in import LeadIn

logger = logging.getLogger(__name__)


class EnrichmentService:
    """Orchestrates lead enrichment: resolve → cache → fetch → extract → score → persist."""

    def __init__(
        self,
        repository: EnrichmentRepository,
        fetcher: WebsiteFetcher,
        text_extractor: TextExtractor,
        profile_extractor: CompanyProfileExtractor,
        domain_resolver: DomainResolver | None = None,
        scorer: LeadScorer | None = None,
        crm_builder: CrmPayloadBuilder | None = None,
    ) -> None:
        self._repo = repository
        self._fetcher = fetcher
        self._text_extractor = text_extractor
        self._profile_extractor = profile_extractor
        self._domain_resolver = domain_resolver or DomainResolver()
        self._scorer = scorer or LeadScorer()
        self._crm_builder = crm_builder or CrmPayloadBuilder()

    async def enrich(self, lead: LeadIn) -> LeadEnriched:
        start = time.monotonic()
        request_id = lead.request_id or uuid4()
        lead = lead.model_copy(update={"request_id": request_id})

        cached_response = self._repo.get_idempotent(request_id)
        if cached_response:
            logger.info("Idempotent hit request_id=%s", request_id)
            return LeadEnriched.model_validate(cached_response)

        domain = self._domain_resolver.resolve(str(lead.email), lead.website)
        if not domain:
            result = self._build_failed(
                request_id, "no_domain", lead, start,
            )
            self._persist(request_id, result)
            return result

        cached_entry = self._repo.get_domain_cache(domain)
        if cached_entry:
            logger.info("Cache hit domain=%s request_id=%s", domain, request_id)
            result = self._build_from_cache(request_id, domain, lead, cached_entry, start)
            self._persist(request_id, result)
            return result

        if not self._repo.check_rate_limit(domain):
            raise RateLimitExceeded(domain)

        fetch_result = await self._fetcher.fetch(domain)
        if not fetch_result.success:
            result = self._build_failed(
                request_id,
                fetch_result.error or "site_unreachable",
                lead,
                start,
                domain=domain,
            )
            self._persist(request_id, result)
            return result

        text = self._text_extractor.extract(fetch_result.html)
        profile, llm_error = await self._profile_extractor.extract(text, domain)

        if llm_error and not profile:
            result = self._build_failed(request_id, llm_error, lead, start, domain=domain)
            self._persist(request_id, result)
            return result

        enrich_status = EnrichStatus.OK
        extraction_confidence = 0.85
        if llm_error:
            enrich_status = EnrichStatus.PARTIAL
            extraction_confidence = 0.5

        profile_typed = profile if isinstance(profile, CompanyProfile) else None
        qualification = self._scorer.score(lead, profile_typed, extraction_confidence)
        crm_data = self._crm_builder.build(lead, profile_typed, qualification, enrich_status)

        result = LeadEnriched(
            request_id=request_id,
            enrich_status=enrich_status,
            domain=domain,
            company_profile=profile_typed,
            lead_qualification=qualification,
            crm_payload=CrmPayload.model_validate(crm_data),
            sources=[fetch_result.url],
            cached=False,
            latency_ms=self._elapsed_ms(start),
            enrich_error=llm_error if enrich_status == EnrichStatus.PARTIAL else None,
        )

        self._repo.save_domain_cache(
            domain,
            DomainCacheEntry(
                enrich_status=enrich_status,
                company_profile=profile_typed.model_dump() if profile_typed else None,
                lead_qualification=qualification.model_dump(),
                sources=[fetch_result.url],
            ),
        )
        self._persist(request_id, result)
        return result

    def _build_from_cache(
        self,
        request_id: UUID,
        domain: str,
        lead: LeadIn,
        cached: DomainCacheEntry,
        start: float,
    ) -> LeadEnriched:
        profile = (
            CompanyProfile.model_validate(cached.company_profile)
            if cached.company_profile
            else None
        )
        cached_qualification = LeadQualification.model_validate(cached.lead_qualification)
        crm_data = self._crm_builder.build(
            lead, profile, cached_qualification, cached.enrich_status,
        )
        return LeadEnriched(
            request_id=request_id,
            enrich_status=cached.enrich_status,
            domain=domain,
            company_profile=profile,
            lead_qualification=cached_qualification,
            crm_payload=CrmPayload.model_validate(crm_data),
            sources=cached.sources or [f"https://{domain}"],
            cached=True,
            latency_ms=self._elapsed_ms(start),
        )

    def _build_failed(
        self,
        request_id: UUID,
        error: str,
        lead: LeadIn,
        start: float,
        domain: Optional[str] = None,
    ) -> LeadEnriched:
        qualification = LeadQualification(tier="unknown", lead_score=0)
        crm_data = self._crm_builder.build(
            lead, None, qualification, EnrichStatus.FAILED,
            extra_tags=["enrich_failed"],
        )
        return LeadEnriched(
            request_id=request_id,
            enrich_status=EnrichStatus.FAILED,
            domain=domain,
            enrich_error=error,
            crm_payload=CrmPayload.model_validate(crm_data),
            lead_qualification=qualification,
            latency_ms=self._elapsed_ms(start),
        )

    def _persist(self, request_id: UUID, result: LeadEnriched) -> None:
        data = result.model_dump(mode="json")
        self._repo.save_idempotent(request_id, data)
        self._repo.log_audit(
            request_id=request_id,
            domain=result.domain,
            enrich_status=result.enrich_status,
            tier=result.lead_qualification.tier,
            lead_score=result.lead_qualification.lead_score,
            cached=result.cached,
            latency_ms=result.latency_ms,
            error_code=result.enrich_error,
            payload=data,
        )

    @staticmethod
    def _elapsed_ms(start: float) -> int:
        return int((time.monotonic() - start) * 1000)
