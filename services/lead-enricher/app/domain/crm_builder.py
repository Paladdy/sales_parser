from typing import Optional

from app.core.enums import EnrichStatus
from app.schemas.company_profile import CompanyProfile
from app.schemas.lead_enriched import LeadQualification
from app.schemas.lead_in import LeadIn


class CrmPayloadBuilder:
    """Builds CRM-ready payload from enriched lead data."""

    @staticmethod
    def build(
        lead: LeadIn,
        profile: Optional[CompanyProfile],
        qualification: LeadQualification,
        enrich_status: str,
        *,
        extra_tags: list[str] | None = None,
    ) -> dict:
        company = profile.company_name if profile and profile.company_name else ""
        display_name = f"{lead.name} — {company}" if company else lead.name

        if enrich_status == EnrichStatus.OK:
            tags = ["enriched"]
        else:
            tags = [f"enrich_{enrich_status}"]

        if lead.utm_source:
            tags.append(f"from_{lead.utm_source}")
        if qualification.tier != "unknown":
            tags.append(f"tier_{qualification.tier}")
        if extra_tags:
            tags.extend(extra_tags)

        custom_fields: dict = {}
        if profile:
            custom_fields = {
                "industry": profile.industry,
                "company_summary": profile.summary,
                "services": ", ".join(profile.services) if profile.services else None,
                "city": profile.city,
                "lead_score": qualification.lead_score,
            }

        return {
            "name": display_name,
            "phone": lead.phone,
            "email": str(lead.email),
            "tags": list(dict.fromkeys(tags)),
            "custom_fields": {k: v for k, v in custom_fields.items() if v},
        }
