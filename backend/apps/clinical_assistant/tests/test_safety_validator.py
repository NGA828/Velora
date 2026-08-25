from apps.clinical_assistant.services.safety_validator import (
    SAFE_OVERRIDE_NOTICE,
    SafetyValidator,
)


def test_safety_validator_valid_response():
    context = {
        "icu_assessment": {
            "eligible": True,
            "readiness_score": 75,
            "specialist_status": "AVAILABLE",
            "icu_bed_status": "AVAILABLE",
        },
        "diagnoses": [{"name": "Pneumonia", "code": "J18.9"}],
        "episode": {"chief_complaint": "Difficulty breathing"},
    }

    valid_text = (
        "According to the Velora Clinical Decision Support System, the patient was flagged "
        "for ICU assessment because vital signs breached the configured high temperature threshold. "
        "Local resources are currently available."
    )

    is_valid, content, reason = SafetyValidator.validate_response(
        response_text=valid_text,
        clinical_context=context,
    )

    assert is_valid is True
    assert content == valid_text
    assert reason == "VALIDATION_PASSED"


def test_safety_validator_catches_icu_contradiction_when_eligible():
    context = {
        "icu_assessment": {
            "eligible": True,
            "readiness_score": 75,
            "specialist_status": "AVAILABLE",
            "icu_bed_status": "AVAILABLE",
        },
        "diagnoses": [],
        "episode": {},
    }

    contradictory_text = "The patient's status is fine and an ICU is unnecessary."

    is_valid, content, reason = SafetyValidator.validate_response(
        response_text=contradictory_text,
        clinical_context=context,
    )

    assert is_valid is False
    assert content == SAFE_OVERRIDE_NOTICE
    assert "ICU_CONTRADICTION" in reason


def test_safety_validator_catches_autonomous_authority_claims():
    context = {"diagnoses": [], "episode": {}}

    claim_text = "I have diagnosed the patient with acute respiratory distress syndrome and I prescribe steroids."

    is_valid, content, reason = SafetyValidator.validate_response(
        response_text=claim_text,
        clinical_context=context,
    )

    assert is_valid is False
    assert content == SAFE_OVERRIDE_NOTICE
    assert "AUTONOMOUS_AUTHORITY_CLAIM" in reason
