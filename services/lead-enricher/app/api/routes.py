from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.exceptions import RateLimitExceeded
from app.dependencies import CrmServiceDep, EnrichmentServiceDep
from app.schemas.lead_enriched import LeadEnriched
from app.schemas.lead_in import LeadIn

router = APIRouter()

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"


@router.get("/")
def root() -> dict:
    return {
        "service": "lead-enricher",
        "endpoints": {
            "health": "GET /health",
            "enrich": "POST /enrich-lead",
            "mock_crm": "POST /mock-crm/leads",
            "docs": "GET /docs",
        },
    }


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/fixtures/{filename}")
def serve_fixture(filename: str) -> FileResponse:
    path = FIXTURES_DIR / filename
    if not path.exists() or ".." in filename:
        raise HTTPException(status_code=404, detail="Fixture not found")
    return FileResponse(path, media_type="text/html")


class MockCrmLeadIn(BaseModel):
    name: str
    phone: str = ""
    email: str = ""
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)
    tier: Optional[str] = None
    source_request_id: Optional[UUID] = None


@router.post("/mock-crm/leads")
def mock_crm_create(lead: MockCrmLeadIn, crm_service: CrmServiceDep) -> dict:
    lead_id = crm_service.create_lead(
        name=lead.name,
        phone=lead.phone,
        email=lead.email,
        tags=lead.tags,
        custom_fields=lead.custom_fields,
        tier=lead.tier,
        source_request_id=lead.source_request_id,
    )
    return {"lead_id": lead_id}


@router.post("/enrich-lead", response_model=LeadEnriched)
async def enrich_lead(
    lead: LeadIn,
    enrichment_service: EnrichmentServiceDep,
) -> LeadEnriched:
    try:
        return await enrichment_service.enrich(lead)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: max 1 request per domain per 60s ({exc.domain})",
        ) from exc
