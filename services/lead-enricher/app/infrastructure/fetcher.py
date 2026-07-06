import logging
from pathlib import Path

import httpx

from app.config import settings
from app.infrastructure.protocols import FetchResult, WebsiteFetcher

logger = logging.getLogger(__name__)

FIXTURE_MAP = {
    "logistics-de.ru": "logistics.html",
    "digital-agency.io": "agency.html",
    "minimal-startup.com": "minimal.html",
    "acme-corp.com": "logistics.html",
}


class HttpxWebsiteFetcher:
    """Fetches company homepage via HTTP; uses local fixtures for demo domains."""

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        self._fixtures_dir = fixtures_dir or (
            Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"
        )

    async def fetch(self, domain: str) -> FetchResult:
        if settings.use_fixture_fetcher or domain in FIXTURE_MAP:
            return await self._fetch_fixture(domain)
        return await self._fetch_http(domain)

    async def _fetch_fixture(self, domain: str) -> FetchResult:
        filename = FIXTURE_MAP.get(domain, "logistics.html")
        path = self._fixtures_dir / filename
        if not path.exists():
            return FetchResult("", f"https://{domain}", False, "fixture_not_found")
        html = path.read_text(encoding="utf-8")
        return FetchResult(html, f"https://{domain}", True)

    async def _fetch_http(self, domain: str) -> FetchResult:
        urls = [f"https://{domain}", f"http://{domain}"]
        timeout = httpx.Timeout(settings.fetch_timeout_sec)
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "LeadEnricher/1.0 (+portfolio demo)"},
        ) as client:
            for url in urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200 and len(resp.text) > 100:
                        return FetchResult(resp.text, str(resp.url), True)
                except httpx.HTTPError as exc:
                    logger.debug("Fetch failed for %s: %s", url, exc)
        return FetchResult("", f"https://{domain}", False, "site_unreachable")
