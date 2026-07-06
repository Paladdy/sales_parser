import pytest

from app.infrastructure.extractor import TrafilaturaTextExtractor
from app.infrastructure.fetcher import HttpxWebsiteFetcher


class TestTextExtractor:
    def test_extracts_logistics_content(self, logistics_html):
        text = TrafilaturaTextExtractor().extract(logistics_html)
        assert "Logistics DE" in text
        assert "freight" in text.lower() or "Freight" in text

    def test_empty_html_returns_empty(self):
        assert TrafilaturaTextExtractor().extract("") == ""

    def test_truncates_long_content(self, logistics_html):
        long_html = logistics_html + "<p>" + ("word " * 5000) + "</p>"
        text = TrafilaturaTextExtractor().extract(long_html)
        assert len(text) <= 8000


@pytest.mark.asyncio
class TestWebsiteFetcher:
    async def test_fixture_domain_returns_html(self):
        fetcher = HttpxWebsiteFetcher()
        result = await fetcher.fetch("logistics-de.ru")
        assert result.success is True
        assert "Logistics DE" in result.html

    async def test_unknown_fixture_domain_uses_default(self):
        fetcher = HttpxWebsiteFetcher()
        result = await fetcher.fetch("acme-corp.com")
        assert result.success is True

    async def test_minimal_fixture(self):
        fetcher = HttpxWebsiteFetcher()
        result = await fetcher.fetch("minimal-startup.com")
        assert result.success is True
        assert "We build stuff" in result.html
