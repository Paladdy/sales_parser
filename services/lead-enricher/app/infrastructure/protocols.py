import logging
from dataclasses import dataclass
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchResult:
    html: str
    url: str
    success: bool
    error: Optional[str] = None


class WebsiteFetcher(Protocol):
    async def fetch(self, domain: str) -> FetchResult: ...


class TextExtractor(Protocol):
    def extract(self, html: str) -> str: ...


class CompanyProfileExtractor(Protocol):
    async def extract(self, text: str, domain: str) -> tuple[Optional[object], Optional[str]]: ...
