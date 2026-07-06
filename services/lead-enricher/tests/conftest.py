import sys
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import build_container
from app.domain.crm_builder import CrmPayloadBuilder
from app.domain.domain_resolver import DomainResolver
from app.domain.lead_scorer import LeadScorer
from app.infrastructure.extractor import TrafilaturaTextExtractor
from app.infrastructure.fetcher import HttpxWebsiteFetcher
from app.infrastructure.protocols import FetchResult
from app.repositories.memory.enrichment_repository import InMemoryEnrichmentRepository
from app.schemas.company_profile import CompanyProfile
from app.schemas.lead_enriched import LeadQualification
from app.schemas.lead_in import LeadIn
from app.services.enrichment_service import EnrichmentService

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def logistics_html() -> str:
    return (FIXTURES_DIR / "logistics.html").read_text(encoding="utf-8")


@pytest.fixture
def logistics_profile() -> CompanyProfile:
    return CompanyProfile(
        company_name="Logistics DE",
        industry="logistics",
        services=["freight", "warehousing"],
        city="Hamburg",
        company_size_hint="sme",
        summary="Logistics company in Hamburg",
    )


@pytest.fixture
def sample_lead() -> LeadIn:
    return LeadIn(
        name="Иван",
        phone="+79991234567",
        email="ivan@logistics-de.ru",
        website="https://logistics-de.ru",
        comment="Нужна реклама для логистической компании",
        utm_source="yandex",
    )


@pytest.fixture
def memory_repo() -> InMemoryEnrichmentRepository:
    return InMemoryEnrichmentRepository()


@pytest.fixture
def mock_profile_extractor(logistics_profile):
    extractor = AsyncMock()
    extractor.extract = AsyncMock(return_value=(logistics_profile, None))
    return extractor


@pytest.fixture
def enrichment_service(memory_repo, mock_profile_extractor) -> EnrichmentService:
    fetcher = HttpxWebsiteFetcher(fixtures_dir=FIXTURES_DIR)
    return EnrichmentService(
        repository=memory_repo,
        fetcher=fetcher,
        text_extractor=TrafilaturaTextExtractor(),
        profile_extractor=mock_profile_extractor,
    )


@pytest.fixture
def test_app(logistics_profile):
    from unittest.mock import AsyncMock

    from fastapi import FastAPI

    from app.api.routes import router
    from app.dependencies import build_container

    application = FastAPI()
    container = build_container(use_memory=True)
    mock_extractor = AsyncMock()
    mock_extractor.extract = AsyncMock(return_value=(logistics_profile, None))
    container.enrichment_service._profile_extractor = mock_extractor
    application.state.container = container
    application.include_router(router)
    return application


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
