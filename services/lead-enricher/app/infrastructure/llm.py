"""Backward-compatible re-export — prefer `from app.llm import OllamaProfileExtractor`."""

from app.llm.ollama import OllamaProfileExtractor

__all__ = ["OllamaProfileExtractor"]
