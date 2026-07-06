import trafilatura
from bs4 import BeautifulSoup

from app.config import settings
from app.infrastructure.protocols import TextExtractor


class TrafilaturaTextExtractor:
    def extract(self, html: str) -> str:
        if not html:
            return ""

        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        )
        if text and len(text.strip()) > 50:
            return self._truncate(text)

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "noscript"]):
            tag.decompose()
        fallback = soup.get_text(separator="\n", strip=True)
        return self._truncate(fallback)

    @staticmethod
    def _truncate(text: str) -> str:
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        if len(text) > settings.max_text_chars:
            return text[: settings.max_text_chars]
        return text
