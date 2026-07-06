from pydantic import BaseModel, Field
from typing import Literal, Optional
from uuid import UUID

from app.schemas.company_profile import CompanyProfile


class LeadQualification(BaseModel):
    is_lpr_likely: bool = False
    signals: list[str] = Field(default_factory=list)
    lead_score: int = 0
    tier: Literal["hot", "warm", "cold", "unknown"] = "unknown"
    confidence: float = 0.0


class CrmPayload(BaseModel):
    name: str = ""
    phone: str = ""
    email: str = ""
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)


class LeadEnriched(BaseModel):
    request_id: UUID
    enrich_status: Literal["ok", "partial", "failed"]
    domain: Optional[str] = None
    company_profile: Optional[CompanyProfile] = None
    lead_qualification: LeadQualification = Field(default_factory=LeadQualification)
    crm_payload: CrmPayload = Field(default_factory=CrmPayload)
    sources: list[str] = Field(default_factory=list)
    cached: bool = False
    latency_ms: int = 0
    enrich_error: Optional[str] = None
