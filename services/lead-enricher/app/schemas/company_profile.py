from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional

_SIZE_ALIASES: dict[str, str] = {
    "solo": "solo",
    "individual": "solo",
    "freelancer": "solo",
    "startup": "solo",
    "small": "solo",
    "sme": "sme",
    "smb": "sme",
    "mid": "sme",
    "medium": "sme",
    "midsized": "sme",
    "mid sized": "sme",
    "mid-sized": "sme",
    "mid_size": "sme",
    "small business": "sme",
    "small and medium": "sme",
    "enterprise": "enterprise",
    "large": "enterprise",
    "corporation": "enterprise",
    "corp": "enterprise",
    "unknown": "unknown",
}


class CompanyProfile(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    services: list[str] = Field(default_factory=list)
    city: Optional[str] = None
    company_size_hint: Optional[Literal["solo", "sme", "enterprise", "unknown"]] = "unknown"
    summary: Optional[str] = None

    @field_validator("company_size_hint", mode="before")
    @classmethod
    def normalize_company_size(cls, value: object) -> str:
        if value is None:
            return "unknown"
        if not isinstance(value, str):
            return "unknown"
        normalized = value.lower().strip()
        if normalized in _SIZE_ALIASES:
            return _SIZE_ALIASES[normalized]
        compact = normalized.replace("-", "").replace("_", "").replace(" ", "")
        for alias, canonical in _SIZE_ALIASES.items():
            if alias.replace("-", "").replace("_", "").replace(" ", "") == compact:
                return canonical
        if any(token in normalized for token in ("enterprise", "large", "corporate")):
            return "enterprise"
        if any(token in normalized for token in ("mid", "medium", "sme", "smb")):
            return "sme"
        if any(token in normalized for token in ("solo", "small", "startup", "individual")):
            return "solo"
        return "unknown"


def normalize_profile_data(data: dict) -> dict:
    """Normalize raw LLM JSON before Pydantic validation."""
    normalized = dict(data)
    if "company_size_hint" in normalized:
        normalized["company_size_hint"] = CompanyProfile.normalize_company_size(
            normalized["company_size_hint"],
        )
    if normalized.get("services") is None:
        normalized["services"] = []
    return normalized
