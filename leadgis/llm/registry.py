"""LLM provider discovery/selection."""

from __future__ import annotations

from leadgis.config import Settings
from leadgis.llm.anthropic_provider import AnthropicLLMProvider
from leadgis.llm.base import LLMProvider
from leadgis.llm.openai_compat import OpenAICompatProvider


def get_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm.provider == "anthropic":
        if not settings.llm.api_key:
            raise ValueError("Anthropic API key is not configured")
        return AnthropicLLMProvider(api_key=settings.llm.api_key, model=settings.llm.model)
    if settings.llm.provider == "openai_compat":
        return OpenAICompatProvider(
            base_url=settings.llm.base_url,
            api_key=settings.llm.api_key,
            model=settings.llm.model,
        )
    raise ValueError(f"Unknown LLM provider: {settings.llm.provider}")
