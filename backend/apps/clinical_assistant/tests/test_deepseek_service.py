from unittest.mock import MagicMock, patch
from decimal import Decimal

import pytest
import requests

from apps.clinical_assistant.services.deepseek_service import (
    DeepSeekService,
    FALLBACK_MESSAGE,
    deepseek_service,
)
from apps.clinical_assistant.services.llm_service import PROVIDERS, LLMService
from apps.vital_signs.models import IcuRecommendation, VitalObservation
from apps.vital_signs.services import record_and_analyze_observation
from apps.vital_signs.tests.test_icu_recommendations import setup_icu_patient


def _mock_success_response(text: str = "The patient has a fever of 39.2C which triggered the high temperature alert."):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {"total_tokens": 120},
    }
    return mock_response


def test_missing_api_key():
    service = LLMService(provider="groq", api_key="")
    result = service.generate_chat_response(
        system_prompt="Test system prompt",
        messages=[{"role": "user", "content": "How is the patient?"}],
    )
    assert result["success"] is False
    assert result["fallback"] is True
    assert result["content"] == FALLBACK_MESSAGE
    assert result["error"] == "API_KEY_NOT_CONFIGURED"


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        LLMService(provider="not-a-real-provider")


def test_default_provider_is_free_groq(monkeypatch):
    for env in ("AI_PROVIDER", "DEEPSEEK_API_KEY", "GROQ_API_KEY", "AI_API_KEY"):
        monkeypatch.delenv(env, raising=False)
    service = LLMService()
    assert service.provider_name == "groq"
    assert service.model == PROVIDERS["groq"]["default_model"]


def test_legacy_deepseek_key_autodetects_deepseek(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "legacy-key")
    service = LLMService()
    assert service.provider_name == "deepseek"
    assert service.api_key == "legacy-key"


@patch("apps.clinical_assistant.services.llm_service.requests.post")
def test_successful_response(mock_post):
    mock_post.return_value = _mock_success_response()

    service = LLMService(provider="groq", api_key="test-key-123")
    result = service.generate_chat_response(
        system_prompt="Test system prompt",
        messages=[{"role": "user", "content": "Why was the patient flagged?"}],
    )

    assert result["success"] is True
    assert result["fallback"] is False
    assert result["provider"] == "groq"
    assert "The patient has a fever" in result["content"]


@patch("apps.clinical_assistant.services.llm_service.requests.post")
def test_timeout_fallback(mock_post):
    mock_post.side_effect = requests.Timeout("Connection timed out")

    service = LLMService(provider="groq", api_key="test-key-123")
    result = service.generate_chat_response(
        system_prompt="Test system prompt",
        messages=[{"role": "user", "content": "Hello"}],
    )

    assert result["success"] is False
    assert result["fallback"] is True
    assert result["content"] == FALLBACK_MESSAGE
    assert result["error"] == "TIMEOUT"


@patch("apps.clinical_assistant.services.llm_service.requests.post")
def test_rate_limit_triggers_fallback_provider(mock_post, monkeypatch):
    """When the primary provider rate-limits (429), the secondary provider answers."""
    rate_limited = MagicMock()
    rate_limited.status_code = 429
    rate_limited.text = "Rate limit reached"
    mock_post.side_effect = [rate_limited, _mock_success_response("Fallback provider answer.")]

    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    service = LLMService(
        provider="groq",
        api_key="groq-key",
        fallback_provider="gemini",
    )
    result = service.generate_chat_response(
        system_prompt="Test system prompt",
        messages=[{"role": "user", "content": "Hello"}],
    )

    assert result["success"] is True
    assert result["fallback"] is False
    assert result["provider"] == "gemini"
    assert result["fallback_provider"] == "gemini"
    assert result["content"] == "Fallback provider answer."


@patch("apps.clinical_assistant.services.llm_service.requests.post")
def test_fallback_provider_without_key_is_skipped(mock_post, monkeypatch):
    rate_limited = MagicMock()
    rate_limited.status_code = 429
    rate_limited.text = "Rate limit reached"
    mock_post.return_value = rate_limited

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    service = LLMService(
        provider="groq",
        api_key="groq-key",
        fallback_provider="gemini",
    )
    result = service.generate_chat_response(
        system_prompt="Test system prompt",
        messages=[{"role": "user", "content": "Hello"}],
    )

    assert result["success"] is False
    assert result["fallback"] is True
    assert result["content"] == FALLBACK_MESSAGE


@patch("apps.clinical_assistant.services.llm_service.requests.post")
def test_server_error_fallback(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response

    service = LLMService(provider="groq", api_key="test-key-123")
    result = service.generate_chat_response(
        system_prompt="Test prompt",
        messages=[{"role": "user", "content": "Test"}],
    )

    assert result["success"] is False
    assert result["fallback"] is True
    assert result["content"] == FALLBACK_MESSAGE


def test_legacy_deepseek_service_still_importable():
    assert isinstance(deepseek_service, LLMService)
    assert issubclass(DeepSeekService, LLMService)
    assert FALLBACK_MESSAGE


@pytest.mark.django_db
def test_core_icu_system_unaffected_when_ai_is_down():
    """
    CRITICAL ARCHITECTURAL RULE:
    The core ICU Recommendation Engine must continue functioning perfectly
    even when the conversational AI provider is completely down or unconfigured.
    """
    doctor, doc_profile, nurse, patient, metric = setup_icu_patient()

    obs = record_and_analyze_observation(
        patient=patient,
        nurse=nurse,
        observed_at=pytest.importorskip("django.utils.timezone").now(),
        values=[{"metric": metric, "value": Decimal("39.2")}],
    )

    # Deterministic ICU recommendation is generated regardless of AI status
    assert obs.status == VitalObservation.Status.CRITICAL
    assert hasattr(obs, "icu_recommendation")
    assert obs.icu_recommendation.eligible is True
    assert obs.icu_recommendation.score is not None
