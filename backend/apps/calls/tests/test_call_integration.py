import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from twilio.request_validator import RequestValidator

from apps.calls.models import CallSession, CallWebhookEvent
from apps.monitoring.tests.test_monitoring_workflow import monitoring_context


@pytest.mark.django_db
def test_call_interface_reports_unavailable_without_twilio():
    doctor, nurse, _, _, _ = monitoring_context()
    client = APIClient()
    client.force_authenticate(doctor)

    availability = client.get(reverse("calls:call-availability"))
    initiation = client.post(
        reverse("calls:call-list"),
        {"recipient": str(nurse.id)},
        format="json",
    )

    assert availability.status_code == 200
    assert availability.json()["available"] is False
    assert initiation.status_code == 503
    assert initiation.json()["error"]["code"] == "integration_unavailable"
    assert CallSession.objects.count() == 0


@pytest.mark.django_db
def test_signed_twilio_voice_and_status_webhooks_update_persisted_call(monkeypatch):
    doctor, nurse, _, _, _ = monitoring_context()
    config = {
        "TWILIO_ACCOUNT_SID": "AC00000000000000000000000000000000",
        "TWILIO_API_KEY": "SK00000000000000000000000000000000",
        "TWILIO_API_SECRET": "secret",
        "TWILIO_TWIML_APP_SID": "AP00000000000000000000000000000000",
        "TWILIO_AUTH_TOKEN": "auth-token",
        "TWILIO_WEBHOOK_BASE_URL": "https://voice.example.test",
    }
    for key, value in config.items():
        monkeypatch.setenv(key, value)
    client = APIClient()
    client.force_authenticate(doctor)
    created = client.post(
        reverse("calls:call-list"),
        {"recipient": str(nurse.id)},
        format="json",
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    validator = RequestValidator(config["TWILIO_AUTH_TOKEN"])
    voice_path = reverse("calls:twilio-voice")
    voice_url = f"{config['TWILIO_WEBHOOK_BASE_URL']}{voice_path}"
    voice_params = {"call_session_id": session_id, "CallSid": "CA123"}
    voice_signature = validator.compute_signature(voice_url, voice_params)
    voice = client.post(
        voice_path,
        voice_params,
        HTTP_X_TWILIO_SIGNATURE=voice_signature,
    )
    assert voice.status_code == 200
    assert b"<Client" in voice.content
    session = CallSession.objects.get(pk=session_id)
    assert session.status == CallSession.Status.RINGING
    assert session.provider_sid == "CA123"

    status_path = f"{reverse('calls:twilio-status')}?call_session_id={session_id}"
    status_url = f"{config['TWILIO_WEBHOOK_BASE_URL']}{status_path}"
    status_params = {"CallSid": "CA123", "CallStatus": "in-progress"}
    status_signature = validator.compute_signature(status_url, status_params)
    progress = client.post(
        status_path,
        status_params,
        HTTP_X_TWILIO_SIGNATURE=status_signature,
    )
    assert progress.status_code == 200
    session.refresh_from_db()
    assert session.status == CallSession.Status.IN_PROGRESS
    assert session.answered_at is not None
    assert CallWebhookEvent.objects.filter(
        call_session=session, processed_at__isnull=False
    ).exists()

    invalid = client.post(status_path, status_params, HTTP_X_TWILIO_SIGNATURE="invalid")
    assert invalid.status_code == 403
