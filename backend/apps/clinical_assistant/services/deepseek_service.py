"""Backwards-compatible facade over the provider-agnostic :mod:`llm_service`.

Historically the Clinical Assistant talked directly to DeepSeek. The assistant
now supports any OpenAI-compatible provider (Groq, Gemini, OpenRouter, Cerebras,
Mistral, SambaNova, DeepSeek) — see ``services/llm_service.py``. This module
keeps the old import paths working.
"""

from __future__ import annotations

from apps.clinical_assistant.services.llm_service import (
    FALLBACK_MESSAGE,
    LLMService,
    PROVIDERS,
    llm_service,
)

__all__ = ["FALLBACK_MESSAGE", "LLMService", "PROVIDERS", "deepseek_service", "llm_service"]


class DeepSeekService(LLMService):
    """Legacy class name for :class:`LLMService` (provider-aware)."""


# Kept for backwards compatibility with older imports/tests.
deepseek_service = llm_service
