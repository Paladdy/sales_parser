from uuid import uuid4

import pytest

from app.core.enums import EnrichStatus
from app.repositories.memory.crm_repository import InMemoryCrmRepository
from app.repositories.memory.enrichment_repository import InMemoryEnrichmentRepository
from app.repositories.protocols import DomainCacheEntry


class TestInMemoryEnrichmentRepository:
    def test_idempotency_roundtrip(self):
        repo = InMemoryEnrichmentRepository()
        rid = uuid4()
        payload = {"request_id": str(rid), "enrich_status": "ok"}
        repo.save_idempotent(rid, payload)
        assert repo.get_idempotent(rid) == payload

    def test_domain_cache_expires(self):
        repo = InMemoryEnrichmentRepository()
        entry = DomainCacheEntry(
            enrich_status="ok",
            company_profile={"company_name": "Test"},
            lead_qualification={"tier": "warm", "lead_score": 50},
            sources=["https://test.com"],
        )
        repo.save_domain_cache("test.com", entry)
        assert repo.get_domain_cache("test.com") is not None

    def test_rate_limit_blocks_within_window(self):
        repo = InMemoryEnrichmentRepository()
        assert repo.check_rate_limit("example.com") is True
        assert repo.check_rate_limit("example.com") is False

    def test_audit_log_appends(self):
        repo = InMemoryEnrichmentRepository()
        rid = uuid4()
        repo.log_audit(rid, "test.com", EnrichStatus.OK, "warm", 60, False, 100, None, {})
        assert len(repo.audit_log) == 1


class TestInMemoryCrmRepository:
    def test_create_lead_increments_id(self):
        repo = InMemoryCrmRepository()
        id1 = repo.create_lead("A", "+1", "a@b.com", [], {}, "warm", None)
        id2 = repo.create_lead("B", "+2", "b@b.com", [], {}, "cold", None)
        assert id1 == 1
        assert id2 == 2
        assert len(repo.leads) == 2
