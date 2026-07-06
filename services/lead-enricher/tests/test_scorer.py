import pytest

from app.config import settings
from app.core.enums import EnrichStatus, LeadTier
from app.domain.crm_builder import CrmPayloadBuilder
from app.domain.lead_scorer import LeadScorer
from app.schemas.company_profile import CompanyProfile
from app.schemas.lead_enriched import LeadQualification
from app.schemas.lead_in import LeadIn


class TestCompanyProfile:
    def test_mid_sized_maps_to_sme(self):
        profile = CompanyProfile.model_validate({
            "company_name": "Test Co",
            "company_size_hint": "mid-sized",
        })
        assert profile.company_size_hint == "sme"

    def test_medium_maps_to_sme(self):
        profile = CompanyProfile(company_size_hint="medium")
        assert profile.company_size_hint == "sme"


class TestLeadScorer:
    def test_warm_tier_with_marketing_comment(self, sample_lead, logistics_profile):
        q = LeadScorer().score(sample_lead, logistics_profile)
        assert q.lead_score >= settings.warm_score_threshold
        assert q.tier in (LeadTier.WARM, LeadTier.HOT)
        assert any("marketing" in s for s in q.signals)

    def test_cold_tier_minimal(self):
        lead = LeadIn(name="Test", phone="+12345678", email="a@corp.com")
        q = LeadScorer().score(lead, None, extraction_confidence=0.3)
        assert q.tier in (LeadTier.COLD, LeadTier.UNKNOWN)
        assert q.lead_score < settings.warm_score_threshold

    def test_hot_threshold(self, sample_lead, logistics_profile):
        profile = logistics_profile.model_copy(update={"company_size_hint": "enterprise"})
        q = LeadScorer(hot_threshold=80, warm_threshold=50).score(
            sample_lead, profile, extraction_confidence=0.9,
        )
        assert q.lead_score >= settings.hot_score_threshold
        assert q.tier == LeadTier.HOT

    def test_lpr_detection(self):
        lead = LeadIn(
            name="CEO",
            phone="+12345678",
            email="ceo@corp.com",
            comment="Я директор компании",
        )
        q = LeadScorer().score(lead, None)
        assert q.is_lpr_likely is True

    def test_score_capped_at_100(self, sample_lead, logistics_profile):
        profile = logistics_profile.model_copy(
            update={"company_size_hint": "enterprise", "services": ["a", "b", "c", "d", "e"]},
        )
        q = LeadScorer().score(sample_lead, profile, extraction_confidence=0.99)
        assert q.lead_score <= 100


class TestCrmPayloadBuilder:
    def test_ok_status_tags(self, sample_lead, logistics_profile):
        q = LeadScorer().score(sample_lead, logistics_profile)
        payload = CrmPayloadBuilder.build(sample_lead, logistics_profile, q, EnrichStatus.OK)
        assert "enriched" in payload["tags"]
        assert "from_yandex" in payload["tags"]
        assert "Logistics DE" in payload["name"]

    def test_failed_status_tags(self, sample_lead):
        q = LeadQualification(tier="unknown", lead_score=0)
        payload = CrmPayloadBuilder.build(
            sample_lead, None, q, EnrichStatus.FAILED, extra_tags=["enrich_failed"],
        )
        assert "enrich_failed" in payload["tags"]

    def test_custom_fields_exclude_empty(self, sample_lead):
        profile = CompanyProfile(company_name="Acme", industry="tech")
        q = LeadQualification(tier="cold", lead_score=10)
        payload = CrmPayloadBuilder.build(sample_lead, profile, q, EnrichStatus.OK)
        assert "industry" in payload["custom_fields"]
        assert "services" not in payload["custom_fields"]

    def test_no_duplicate_tags(self, sample_lead, logistics_profile):
        q = LeadScorer().score(sample_lead, logistics_profile)
        payload = CrmPayloadBuilder.build(
            sample_lead, logistics_profile, q, EnrichStatus.OK, extra_tags=["enriched"],
        )
        assert payload["tags"].count("enriched") == 1
