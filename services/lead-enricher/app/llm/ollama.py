import json
import logging
import re
from typing import Optional

import httpx
from pydantic import ValidationError

from app.config import settings
from app.schemas.company_profile import CompanyProfile, normalize_profile_data

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a B2B lead enrichment assistant. Extract company information from the website text below.

Return ONLY valid JSON with this exact schema (no markdown, no explanation):
{{
  "company_name": "string or null",
  "industry": "string or null",
  "services": ["list of services/products"],
  "city": "string or null",
  "company_size_hint": "solo|sme|enterprise|unknown",
  "summary": "1-2 sentence company description"
}}

Website domain: {domain}
Website text:
{text}
"""


class OllamaProfileExtractor:
    """Ollama client: structured JSON extraction with Pydantic validation and repair retries."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url or settings.ollama_base_url
        self._model = model or settings.ollama_model
        self._http_client = http_client

    async def extract(self, text: str, domain: str) -> tuple[Optional[CompanyProfile], Optional[str]]:
        if not text or len(text.strip()) < 30:
            return None, "empty_text"

        if not await self._is_available():
            return self._fallback_profile(domain, text), "ollama_unavailable"

        prompt = EXTRACTION_PROMPT.format(domain=domain, text=text)
        last_error: Optional[str] = None

        for _ in range(settings.llm_max_retries + 1):
            try:
                raw = await self._call_ollama(prompt)
                data = normalize_profile_data(self._parse_json(raw))
                return CompanyProfile.model_validate(data), None
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = f"llm_invalid_json: {exc}"
                prompt = EXTRACTION_PROMPT.format(domain=domain, text=text)
                prompt += f"\n\nFix JSON error: {exc}"
            except httpx.HTTPStatusError as exc:
                last_error = (
                    "ollama_unavailable"
                    if exc.response.status_code == 404
                    else f"ollama_error: {exc.response.status_code}"
                )
                break
            except httpx.HTTPError:
                last_error = "ollama_unavailable"
                break

        return self._fallback_profile(domain, text), last_error

    async def _is_available(self) -> bool:
        try:
            if self._http_client:
                resp = await self._http_client.get(f"{self._base_url}/api/tags")
            else:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{self._base_url}/api/tags")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def _call_ollama(self, prompt: str) -> str:
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": settings.llm_temperature},
        }
        if self._http_client:
            resp = await self._http_client.post(f"{self._base_url}/api/generate", json=payload)
        else:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(f"{self._base_url}/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json().get("response", "")

    @staticmethod
    def _parse_json(raw: str) -> dict:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)

    @staticmethod
    def _fallback_profile(domain: str, text: str) -> CompanyProfile:
        industry = "unknown"
        lower = text.lower()
        if any(w in lower for w in ("logistics", "freight", "shipping", "warehouse")):
            industry = "logistics"
        elif any(w in lower for w in ("marketing", "digital", "agency", "advertising")):
            industry = "marketing"
        elif any(w in lower for w in ("software", "development", "saas", "tech")):
            industry = "technology"

        name = domain.split(".")[0].replace("-", " ").title()
        summary = text[:200].strip() if text else f"Company at {domain}"

        return CompanyProfile(
            company_name=name,
            industry=industry,
            services=[],
            city=None,
            company_size_hint="unknown",
            summary=summary,
        )
