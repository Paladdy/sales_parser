from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from app.config import settings
from app.infrastructure.extractor import TrafilaturaTextExtractor
from app.infrastructure.fetcher import HttpxWebsiteFetcher
from app.llm import OllamaProfileExtractor
from app.repositories.memory.crm_repository import InMemoryCrmRepository
from app.repositories.memory.enrichment_repository import InMemoryEnrichmentRepository
from app.repositories.postgres.repositories import PostgresCrmRepository, PostgresEnrichmentRepository
from app.services.crm_service import CrmService
from app.services.enrichment_service import EnrichmentService


@dataclass
class AppContainer:
    enrichment_repo: PostgresEnrichmentRepository | InMemoryEnrichmentRepository
    crm_repo: PostgresCrmRepository | InMemoryCrmRepository
    enrichment_service: EnrichmentService
    crm_service: CrmService

    def startup(self) -> None:
        if isinstance(self.enrichment_repo, PostgresEnrichmentRepository):
            self.enrichment_repo.open()
            if not self.enrichment_repo.ping():
                raise RuntimeError("Cannot connect to PostgreSQL")
        if isinstance(self.crm_repo, PostgresCrmRepository):
            self.crm_repo.open()

    def shutdown(self) -> None:
        if isinstance(self.enrichment_repo, PostgresEnrichmentRepository):
            self.enrichment_repo.close()
        if isinstance(self.crm_repo, PostgresCrmRepository):
            self.crm_repo.close()


def build_container(use_memory: bool = False) -> AppContainer:
    fetcher = HttpxWebsiteFetcher()
    text_extractor = TrafilaturaTextExtractor()
    profile_extractor = OllamaProfileExtractor()

    if use_memory:
        enrichment_repo = InMemoryEnrichmentRepository()
        crm_repo = InMemoryCrmRepository()
    else:
        enrichment_repo = PostgresEnrichmentRepository(settings.database_url)
        crm_repo = PostgresCrmRepository(settings.database_url)

    enrichment_service = EnrichmentService(
        repository=enrichment_repo,
        fetcher=fetcher,
        text_extractor=text_extractor,
        profile_extractor=profile_extractor,
    )
    crm_service = CrmService(repository=crm_repo)

    return AppContainer(
        enrichment_repo=enrichment_repo,
        crm_repo=crm_repo,
        enrichment_service=enrichment_service,
        crm_service=crm_service,
    )


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


ContainerDep = Annotated[AppContainer, Depends(get_container)]


def get_enrichment_service(container: ContainerDep) -> EnrichmentService:
    return container.enrichment_service


def get_crm_service(container: ContainerDep) -> CrmService:
    return container.crm_service


EnrichmentServiceDep = Annotated[EnrichmentService, Depends(get_enrichment_service)]
CrmServiceDep = Annotated[CrmService, Depends(get_crm_service)]
