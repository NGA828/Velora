"""Provider-agnostic conversational LLM service for the Clinical Assistant.

The assistant uses any OpenAI-compatible chat-completions endpoint. This keeps
Velora deployable for free: several providers (Groq, Google Gemini, OpenRouter,
Cerebras, Mistral, SambaNova) offer standing free tiers whose daily limits are
far above the project's requirement of ~20 messages/day.

Configuration (environment variables):

- ``AI_PROVIDER``           primary provider id (see ``PROVIDERS`` below).
- ``AI_API_KEY``            key for the primary provider (or a provider-specific
                            variable such as ``GROQ_API_KEY``).
- ``AI_MODEL``              override the provider's default model.
- ``AI_BASE_URL``           override the provider's default base URL.
- ``AI_FALLBACK_PROVIDER``  optional secondary provider used automatically when
                            the primary fails (rate limit, timeout, outage).
- ``AI_TIMEOUT``            request timeout in seconds (default 30).

Legacy DeepSeek variables (``DEEPSEEK_API_KEY`` / ``DEEPSEEK_MODEL`` /
``DEEPSEEK_BASE_URL``) keep working for backwards compatibility.

Free-tier snapshot (verify current limits on each provider's console):
- groq        ~30 req/min, ~1,000 req/day (no credit card)
- gemini      ~10-15 req/min, ~250-1,500 req/day (no credit card)
- openrouter  ~20 req/min, 50 req/day (1,000/day after a one-time $10 top-up)
- cerebras    ~1M tokens/day (no credit card)
- mistral     ~1B tokens/month (no credit card)
- sambanova   ~200K tokens/day per model (no credit card)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = (
    "The conversational assistant is temporarily unavailable. "
    "Please refer to the Clinical Decision Support recommendation on the dashboard "
    "and contact the attending medical team for further assistance."
)

# Every provider below exposes an OpenAI-compatible /chat/completions endpoint,
# so switching providers never requires code changes - only environment config.
PROVIDERS: dict[str, dict[str, Any]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "openai/gpt-oss-120b",
        "key_envs": ("GROQ_API_KEY",),
        "docs": "https://console.groq.com",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-2.5-flash",
        "key_envs": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "docs": "https://aistudio.google.com",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
        "key_envs": ("OPENROUTER_API_KEY",),
        "docs": "https://openrouter.ai",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "default_model": "llama-3.3-70b",
        "key_envs": ("CEREBRAS_API_KEY",),
        "docs": "https://cloud.cerebras.ai",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-small-latest",
        "key_envs": ("MISTRAL_API_KEY",),
        "docs": "https://console.mistral.ai",
    },
    "sambanova": {
        "base_url": "https://api.sambanova.ai/v1",
        "default_model": "Meta-Llama-3.3-70B-Instruct",
        "key_envs": ("SAMBANOVA_API_KEY",),
        "docs": "https://cloud.sambanova.ai",
    },
    # Legacy paid provider, kept so existing deployments keep working.
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "key_envs": ("DEEPSEEK_API_KEY",),
        "docs": "https://platform.deepseek.com",
    },
}


class LLMService:
    """Chat-completions client with automatic provider failover."""

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
        fallback_provider: str | None = None,
    ) -> None:
        self.provider_name = self._resolve_provider(provider)
        self.api_key = api_key or self._resolve_key(self.provider_name)
        self.model = model or os.getenv("AI_MODEL", "") or PROVIDERS[self.provider_name]["default_model"]
        self.base_url = (base_url or os.getenv("AI_BASE_URL", "") or PROVIDERS[self.provider_name]["base_url"]).rstrip("/")
        self.timeout = timeout or int(os.getenv("AI_TIMEOUT", "30"))
        self.fallback_provider_name = fallback_provider or os.getenv("AI_FALLBACK_PROVIDER", "").strip().lower() or None

    # ------------------------------------------------------------------ #
    # Configuration resolution
    # ------------------------------------------------------------------ #
    @staticmethod
    def _resolve_provider(provider: str | None) -> str:
        explicit = (provider or os.getenv("AI_PROVIDER", "")).strip().lower()
        if explicit:
            if explicit not in PROVIDERS:
                raise ValueError(
                    f"Unknown AI provider '{explicit}'. Valid providers: {', '.join(sorted(PROVIDERS))}"
                )
            return explicit

        # Auto-detect from provider-specific keys, preferring the legacy
        # DeepSeek key so existing deployments behave exactly as before.
        if os.getenv("DEEPSEEK_API_KEY", "").strip():
            return "deepseek"
        for name, config in PROVIDERS.items():
            for env in config["key_envs"]:
                if os.getenv(env, "").strip():
                    return name
        return "groq"  # best free default (no credit card, ~1k requests/day)

    @staticmethod
    def _resolve_key(provider: str) -> str:
        config = PROVIDERS[provider]
        for env in (*config["key_envs"], "AI_API_KEY"):
            value = os.getenv(env, "").strip()
            if value:
                return value
        return ""

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def generate_chat_response(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        """Call the configured provider (plus optional fallback).

        Returns ``{"success", "content", "error", "fallback", "usage", "provider"}``.
        Never raises: any failure degrades to the deterministic fallback message
        so the ICU Recommendation System keeps working independently.
        """
        payload_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            if msg.get("role") in {"user", "assistant"}:
                payload_messages.append({"role": msg["role"], "content": msg["content"]})

        result = self._call_provider(
            provider=self.provider_name,
            api_key=self.api_key,
            model=self.model,
            base_url=self.base_url,
            payload_messages=payload_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if not result["success"] and self.fallback_provider_name:
            fallback = self._try_fallback(
                payload_messages=payload_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                primary_error=result.get("error"),
            )
            if fallback is not None:
                return fallback

        return result

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _try_fallback(
        self,
        *,
        payload_messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        primary_error: str | None,
    ) -> dict[str, Any] | None:
        name = self.fallback_provider_name
        if name not in PROVIDERS:
            logger.warning("Configured AI_FALLBACK_PROVIDER '%s' is unknown; skipping fallback.", name)
            return None

        config = PROVIDERS[name]
        api_key = ""
        for env in (*config["key_envs"], "AI_API_KEY"):
            api_key = os.getenv(env, "").strip()
            if api_key:
                break

        if not api_key:
            logger.info("Fallback provider '%s' has no API key configured; skipping.", name)
            return None

        logger.warning(
            "Primary AI provider '%s' failed (%s); retrying with fallback provider '%s'.",
            self.provider_name,
            primary_error,
            name,
        )
        result = self._call_provider(
            provider=name,
            api_key=api_key,
            model=os.getenv("AI_FALLBACK_MODEL", "") or config["default_model"],
            base_url=os.getenv("AI_FALLBACK_BASE_URL", "") or config["base_url"],
            payload_messages=payload_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if result["success"]:
            result["fallback_provider"] = name
        return result

    def _call_provider(
        self,
        *,
        provider: str,
        api_key: str,
        model: str,
        base_url: str,
        payload_messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        if not api_key:
            logger.warning(
                "AI provider '%s' has no API key configured. Returning fallback message. "
                "Set AI_API_KEY (or the provider-specific variable) to enable the assistant.",
                provider,
            )
            return {
                "success": False,
                "content": FALLBACK_MESSAGE,
                "error": "API_KEY_NOT_CONFIGURED",
                "fallback": True,
                "usage": None,
                "provider": provider,
            }

        endpoint = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # OpenRouter routing metadata (ignored by other providers).
        if provider == "openrouter":
            headers["HTTP-Referer"] = os.getenv("AI_OPENROUTER_REFERER", "https://velora.app")
            headers["X-Title"] = "Velora Clinical Assistant"

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json={
                    "model": model,
                    "messages": payload_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=self.timeout,
            )

            if response.status_code != 200:
                logger.error(
                    "AI provider '%s' (%s) returned error status %s: %s",
                    provider,
                    model,
                    response.status_code,
                    response.text[:200],
                )
                return {
                    "success": False,
                    "content": FALLBACK_MESSAGE,
                    "error": f"HTTP_{response.status_code}: {response.text[:200]}",
                    "fallback": True,
                    "usage": None,
                    "provider": provider,
                }

            data = response.json()
            choices = data.get("choices", [])
            if not choices or not choices[0].get("message", {}).get("content"):
                logger.error("AI provider '%s' returned empty choices or missing content: %s", provider, data)
                return {
                    "success": False,
                    "content": FALLBACK_MESSAGE,
                    "error": "EMPTY_RESPONSE",
                    "fallback": True,
                    "usage": None,
                    "provider": provider,
                }

            content = choices[0]["message"]["content"].strip()
            return {
                "success": True,
                "content": content,
                "error": None,
                "fallback": False,
                "usage": data.get("usage"),
                "provider": provider,
            }

        except requests.Timeout as exc:
            logger.error("AI provider '%s' timed out: %s", provider, exc)
            return {
                "success": False,
                "content": FALLBACK_MESSAGE,
                "error": "TIMEOUT",
                "fallback": True,
                "usage": None,
                "provider": provider,
            }
        except requests.RequestException as exc:
            logger.error("AI provider '%s' network/request error: %s", provider, exc)
            return {
                "success": False,
                "content": FALLBACK_MESSAGE,
                "error": str(exc),
                "fallback": True,
                "usage": None,
                "provider": provider,
            }
        except Exception as exc:  # pragma: no cover - defensive catch-all
            logger.exception("Unexpected error calling AI provider '%s': %s", provider, exc)
            return {
                "success": False,
                "content": FALLBACK_MESSAGE,
                "error": str(exc),
                "fallback": True,
                "usage": None,
                "provider": provider,
            }

    def describe(self) -> dict[str, Any]:
        """Human-readable configuration summary (used in diagnostics/docs)."""
        return {
            "provider": self.provider_name,
            "model": self.model,
            "base_url": self.base_url,
            "key_configured": bool(self.api_key),
            "fallback_provider": self.fallback_provider_name,
            "free_tier": self.provider_name in {"groq", "gemini", "openrouter", "cerebras", "mistral", "sambanova"},
        }


llm_service = LLMService()
