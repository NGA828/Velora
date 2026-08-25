from unittest.mock import MagicMock, patch
from decimal import Decimal
import pytest
import requests

from apps.clinical_assistant.services.deepseek_service import (
    DeepSeekService,
    FALLBACK_MESSAGE,
)
from apps.vital_signs.models import IcuRecommendation, VitalObservation
from apps.vital_signs.services import record_and_analyze_observation
from apps.vital_signs.tests.test_icu_recommendations import setup_icu_patient


def test_deepseek_missing_api_key():
    service = DeepSeekService(api_key="")
    result = service.generate_chat_response(
        system_prompt="Test system prompt",
        messages=[{"role": "user", "content": "How is the patient?"}],
    )
    assert result["success"] is False
    assert result["fallback"] is True
    assert result["content"] == FALLBACK_MESSAGE


@patch("apps.clinical_assistant.services.deepseek_service.requests.post")
def test_deepseek_successful_response(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "The patient has a fever of 39.2C which triggered the high temperature alert.",
                }
            }
        ],
        "usage": {"total_tokens": 120},
    }
    mock_post.return_value = mock_response

    service = DeepSeekService(api_key="test-key-123")
    result = service.generate_chat_response(
        system_prompt="Test system prompt",
        messages=[{"role": "user", "content": "Why was the patient flagged?"}],
    )

    assert result["success"] is True
    assert result["fallback"] is False
    assert "The patient has a fever" in result["content"]


@patch("apps.clinical_assistant.services.deepseek_service.requests.post")
def test_deepseek_timeout_fallback(mock_post):
    mock_post.side_effect = requests.Timeout("Connection timed out")

    service = DeepSeekService(api_key="test-key-123")
    result = service.generate_chat_response(
        system_prompt="Test system prompt",
        messages=[{"role": "user", "content": "Hello"}],
    )

    assert result["success"] is False
    assert result["fallback"] is True
    assert result["content"] == FALLBACK_MESSAGE
    assert result["error"] == "TIMEOUT"


@patch("apps.clinical_assistant.services.deepseek_service.requests.post")
def test_deepseek_server_error_fallback(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response

    service = DeepSeekService(api_key="test-key-123")
    result = service.generate_chat_response(
        system_prompt="Test prompt",
        messages=[{"role": "user", "content": "Test"}],
    )

    assert result["success"] is False
    assert result["fallback"] is True
    assert result["content"] == FALLBACK_MESSAGE


@pytest.mark.django_db
def test_core_icu_system_unaffected_when_deepseek_is_down():
    """
    CRITICAL ARCHITECTURAL RULE:
    The core ICU Recommendation Engine must continue functioning perfectly
    even when DeepSeek is completely down or unconfigured.
    """
    doctor, doc_profile, nurse, patient, metric = setup_icu_patient()

    obs = record_and_analyze_observation(
        patient=patient,
        nurse=nurse,
        observed_at=timezone.now() if "timezone" in globals() else None or pytest.importorskip("django.utils.timezone").now(),
        values=[{"metric": metric, "value": Decimal("39.2")}],
    )

    # Deterministic ICU recommendation is generated regardless of DeepSeek status
    assert obs.status == VitalObservation.Status.CRITICAL
    assert hasattr(obs, "icu_recommendation")
    assert obs.icu_recommendation.eligible is True
    assert obs.icu_recommendation.score is not None
