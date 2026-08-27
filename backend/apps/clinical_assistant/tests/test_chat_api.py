from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.clinical_assistant.models import (
    AssistantAuditLog,
    AssistantMessage,
    AssistantSession,
)
from apps.identity.models import Invitation, PatientGuardProfile, UserRole
from apps.identity.tests.factories import create_staff, create_user
from apps.patients.models import GuardianAccess
from apps.vital_signs.services import record_and_analyze_observation
from apps.vital_signs.tests.test_icu_recommendations import setup_icu_patient


@pytest.mark.django_db
@patch("apps.clinical_assistant.services.llm_service.requests.post")
def test_doctor_chat_endpoint_success(mock_post):
    from apps.clinical_assistant.services.deepseek_service import deepseek_service
    deepseek_service.api_key = "mock-test-key"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "The patient was flagged for ICU assessment due to critical temperature of 39.2C.",
                }
            }
        ],
        "usage": {"total_tokens": 80},
    }
    mock_post.return_value = mock_response

    doctor, doc_profile, nurse, patient, metric = setup_icu_patient()

    # Record critical observation
    record_and_analyze_observation(
        patient=patient,
        nurse=nurse,
        observed_at=timezone.now(),
        values=[{"metric": metric, "value": Decimal("39.2")}],
    )

    client = APIClient()
    client.force_authenticate(doctor)

    response = client.post(
        reverse("clinical-assistant-chat"),
        {
            "patient_id": str(patient.id),
            "message": "Why was this patient flagged for ICU?",
        },
        format="json",
    )

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["message"]["role"] == "assistant"
    assert "The patient was flagged" in data["message"]["content"]
    assert data["context_summary"]["icu_eligible"] is True

    # Check persistence
    session = AssistantSession.objects.get(pk=data["session_id"])
    assert session.messages.count() == 2
    assert session.messages.first().role == AssistantMessage.Role.USER
    assert session.messages.last().role == AssistantMessage.Role.ASSISTANT

    # Check audit log
    audit_log = AssistantAuditLog.objects.filter(patient=patient).first()
    assert audit_log is not None
    assert audit_log.user == doctor


@pytest.mark.django_db
def test_unauthorized_user_chat_rejected():
    doctor, doc_profile, nurse, patient, metric = setup_icu_patient()
    other_doctor, _ = create_staff(
        role=UserRole.DOCTOR, email="unauthorized_doc@example.org", employee_number="DOC-UNAUTH-001"
    )

    client = APIClient()
    client.force_authenticate(other_doctor)

    response = client.post(
        reverse("clinical-assistant-chat"),
        {
            "patient_id": str(patient.id),
            "message": "Give me patient vitals",
        },
        format="json",
    )

    assert response.status_code in {403, 404}


@pytest.mark.django_db
@patch("apps.clinical_assistant.services.llm_service.requests.post")
def test_patient_guard_chat_endpoint_success(mock_post):
    from apps.clinical_assistant.services.deepseek_service import deepseek_service
    deepseek_service.api_key = "mock-test-key"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Your loved one has a high temperature and the medical team is providing close care.",
                }
            }
        ],
        "usage": {"total_tokens": 50},
    }
    mock_post.return_value = mock_response

    doctor, doc_profile, nurse, patient, metric = setup_icu_patient()

    guard_user = create_user(role=UserRole.PATIENT_GUARD, email="guard_chat@example.org")
    guard_profile = PatientGuardProfile.objects.create(user=guard_user)
    invitation = Invitation.objects.create(
        email="guard_chat@example.org",
        intended_role=UserRole.PATIENT_GUARD,
        token_hash="token-hash-3",
        invited_by=doctor,
        expires_at=timezone.now() + timezone.timedelta(days=7),
    )
    GuardianAccess.objects.create(
        patient=patient,
        guardian=guard_profile,
        invitation=invitation,
        relationship="Daughter",
        status=GuardianAccess.Status.ACTIVE,
        granted_by=doctor,
        granted_at=timezone.now(),
    )

    client = APIClient()
    client.force_authenticate(guard_user)

    response = client.post(
        reverse("clinical-assistant-chat"),
        {
            "patient_id": str(patient.id),
            "message": "Is my father okay?",
        },
        format="json",
    )

    assert response.status_code == 200
    data = response.json()
    assert "Your loved one" in data["message"]["content"]


@pytest.mark.django_db
def test_session_list_and_clear():
    doctor, doc_profile, nurse, patient, metric = setup_icu_patient()
    session = AssistantSession.objects.create(user=doctor, patient=patient)
    AssistantMessage.objects.create(session=session, role="user", content="Hello")
    AssistantMessage.objects.create(session=session, role="assistant", content="Hi Doctor")

    client = APIClient()
    client.force_authenticate(doctor)

    list_resp = client.get(reverse("clinical-assistant-sessions-list"))
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) == 1

    clear_resp = client.post(reverse("clinical-assistant-sessions-clear-messages", kwargs={"pk": session.id}))
    assert clear_resp.status_code == 200
    assert session.messages.count() == 0
