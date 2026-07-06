from app.core.compat import StrEnum


class EnrichStatus(StrEnum):
    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


class EnrichError(StrEnum):
    NO_DOMAIN = "no_domain"
    SITE_UNREACHABLE = "site_unreachable"
    FIXTURE_NOT_FOUND = "fixture_not_found"
    EMPTY_TEXT = "empty_text"
    OLLAMA_UNAVAILABLE = "ollama_unavailable"
    OLLAMA_ERROR = "ollama_error"
    LLM_INVALID_JSON = "llm_invalid_json"
    RATE_LIMITED = "rate_limited"


class LeadTier(StrEnum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    UNKNOWN = "unknown"
