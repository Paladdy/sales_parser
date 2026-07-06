import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.llm import OllamaProfileExtractor


@pytest.mark.asyncio
class TestOllamaProfileExtractor:
    async def test_empty_text_returns_error(self):
        extractor = OllamaProfileExtractor()
        profile, error = await extractor.extract("", "test.com")
        assert profile is None
        assert error == "empty_text"

    async def test_fallback_when_ollama_unavailable(self, logistics_html):
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=httpx.ConnectError("down"))
        extractor = OllamaProfileExtractor(http_client=client)
        profile, error = await extractor.extract(logistics_html, "logistics-de.ru")
        assert profile is not None
        assert profile.industry == "logistics"
        assert error == "ollama_unavailable"

    async def test_successful_extraction(self, logistics_html):
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=MagicMock(status_code=200))
        client.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {"response": json.dumps({
                "company_name": "Logistics DE",
                "industry": "logistics",
                "services": ["freight"],
                "city": "Hamburg",
                "company_size_hint": "sme",
                "summary": "Freight company",
            })},
        ))
        extractor = OllamaProfileExtractor(http_client=client)
        profile, error = await extractor.extract(logistics_html, "logistics-de.ru")
        assert error is None
        assert profile.company_name == "Logistics DE"

    async def test_json_repair_retry(self, logistics_html):
        valid = json.dumps({
            "company_name": "Logistics DE",
            "industry": "logistics",
            "services": [],
            "city": None,
            "company_size_hint": "sme",
            "summary": "Ok",
        })
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=MagicMock(status_code=200))
        client.post = AsyncMock(side_effect=[
            MagicMock(status_code=200, json=lambda: {"response": "broken"}),
            MagicMock(status_code=200, json=lambda: {"response": valid}),
        ])
        extractor = OllamaProfileExtractor(http_client=client)
        profile, error = await extractor.extract(logistics_html, "logistics-de.ru")
        assert profile is not None
        assert profile.company_name == "Logistics DE"
        assert error is None


class TestOllamaJsonParsing:
    def test_parse_json_strips_markdown_fence(self):
        raw = '```json\n{"company_name": "Test"}\n```'
        data = OllamaProfileExtractor._parse_json(raw)
        assert data["company_name"] == "Test"
