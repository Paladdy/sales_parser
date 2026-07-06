from uuid import uuid4

import pytest


@pytest.mark.asyncio
class TestEnrichAPI:
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_enrich_lead_success(self, client):
        resp = await client.post("/enrich-lead", json={
            "request_id": str(uuid4()),
            "name": "Иван",
            "phone": "+79991234567",
            "email": "ivan@logistics-de.ru",
            "comment": "Нужна реклама",
            "utm_source": "yandex",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["enrich_status"] == "ok"
        assert data["domain"] == "logistics-de.ru"
        assert data["company_profile"]["company_name"] == "Logistics DE"

    async def test_enrich_no_domain(self, client):
        resp = await client.post("/enrich-lead", json={
            "request_id": str(uuid4()),
            "name": "Test",
            "phone": "+79991234567",
            "email": "user@gmail.com",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["enrich_status"] == "failed"
        assert data["enrich_error"] == "no_domain"

    async def test_mock_crm_create(self, client):
        resp = await client.post("/mock-crm/leads", json={
            "name": "Test Lead",
            "phone": "+7999",
            "email": "test@corp.com",
            "tags": ["enriched"],
            "tier": "warm",
        })
        assert resp.status_code == 200
        assert "lead_id" in resp.json()

    async def test_fixture_endpoint(self, client):
        resp = await client.get("/fixtures/logistics.html")
        assert resp.status_code == 200
        assert "Logistics DE" in resp.text

    async def test_rate_limit_returns_429(self, client, test_app):
        payload = {
            "request_id": str(uuid4()),
            "name": "Иван",
            "phone": "+79991234567",
            "email": "ivan@logistics-de.ru",
        }
        resp1 = await client.post("/enrich-lead", json=payload)
        assert resp1.status_code == 200

        payload["request_id"] = str(uuid4())
        test_app.state.container.enrichment_repo.domain_cache.clear()

        resp2 = await client.post("/enrich-lead", json=payload)
        assert resp2.status_code == 429
