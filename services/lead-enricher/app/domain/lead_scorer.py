from typing import Optional

from app.config import settings
from app.core.enums import LeadTier
from app.schemas.company_profile import CompanyProfile
from app.schemas.lead_enriched import LeadQualification
from app.schemas.lead_in import LeadIn

BUYING_KEYWORDS = (
    "реклам", "marketing", "нужн", "need", "budget", "бюджет",
    "срочно", "urgent", "заказ", "order", "интерес", "interest",
)
LPR_KEYWORDS = ("директор", "ceo", "founder", "owner", "владел")
QUALITY_UTM_SOURCES = frozenset({"yandex", "google", "direct"})


class LeadScorer:
    """Rule-based lead qualification from profile and form signals."""

    def __init__(
        self,
        hot_threshold: int | None = None,
        warm_threshold: int | None = None,
    ) -> None:
        self._hot = hot_threshold if hot_threshold is not None else settings.hot_score_threshold
        self._warm = warm_threshold if warm_threshold is not None else settings.warm_score_threshold

    def score(
        self,
        lead: LeadIn,
        profile: Optional[CompanyProfile],
        extraction_confidence: float = 0.7,
    ) -> LeadQualification:
        score = 0
        signals: list[str] = []

        if profile and profile.company_name:
            score += 15
            signals.append("company identified")

        if profile and profile.industry and profile.industry != "unknown":
            score += 10
            signals.append(f"industry: {profile.industry}")

        if profile and profile.services:
            score += min(len(profile.services) * 5, 15)

        if profile and profile.company_size_hint == "enterprise":
            score += 20
            signals.append("enterprise size hint")
        elif profile and profile.company_size_hint == "sme":
            score += 10

        comment = (lead.comment or "").lower()
        if comment:
            matched = [kw for kw in BUYING_KEYWORDS if kw in comment]
            if matched:
                score += min(len(matched) * 8, 24)
                signals.append("comment mentions marketing need")

        if lead.website:
            score += 5

        if lead.utm_source in QUALITY_UTM_SOURCES:
            score += 5

        is_lpr = any(w in comment for w in LPR_KEYWORDS)
        tier = self._tier_from_score(score)
        confidence = min(extraction_confidence + (score / 200), 0.95)

        return LeadQualification(
            is_lpr_likely=is_lpr,
            signals=signals,
            lead_score=min(score, 100),
            tier=tier,
            confidence=round(confidence, 2),
        )

    def _tier_from_score(self, score: int) -> str:
        if score >= self._hot:
            return LeadTier.HOT
        if score >= self._warm:
            return LeadTier.WARM
        if score > 0:
            return LeadTier.COLD
        return LeadTier.UNKNOWN
