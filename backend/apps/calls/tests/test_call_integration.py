from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
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


@pytest.mark.django_db
def test_webrtc_offer_and_answer_are_persisted_for_late_accept():
    """The callee must be able to recover the offer/answer from the API even
    when the realtime delivery was missed (e.g. they were on another page)."""
    doctor, nurse, _, _, _ = monitoring_context()
    doctor_client = APIClient()
    doctor_client.force_authenticate(doctor)
    created = doctor_client.post(
        reverse("calls:call-list"),
        {"recipient": str(nurse.id), "provider": "WEBRTC"},
        format="json",
    )
    assert created.status_code == 201
    session_id = created.json()["id"]
    assert created.json()["status"] == CallSession.Status.QUEUED

    offer = "v=0\r\no=- 4611722893312512233 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n"
    relayed = doctor_client.post(
        reverse("calls:call-signal", args=[session_id]),
        {"to_user": str(nurse.id), "data": {"type": "offer", "sdp": offer}},
        format="json",
    )
    assert relayed.status_code == 202

    # The callee fetches the call detail after the incoming event and gets the
    # persisted offer even though their socket may have missed the signal.
    nurse_client = APIClient()
    nurse_client.force_authenticate(nurse)
    detail = nurse_client.get(reverse("calls:call-detail", args=[session_id]))
    assert detail.status_code == 200
    assert detail.json()["offer_sdp"] == offer
    assert detail.json()["offer_from"] == str(doctor.id)
    assert detail.json()["answer_sdp"] == ""

    answer = "v=0\r\no=- 7017249262185250846 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n"
    answered = nurse_client.post(
        reverse("calls:call-signal", args=[session_id]),
        {"to_user": str(doctor.id), "data": {"type": "answer", "sdp": answer}},
        format="json",
    )
    assert answered.status_code == 202

    # The caller can recover the answer the same way if its socket missed it.
    detail = doctor_client.get(reverse("calls:call-detail", args=[session_id]))
    assert detail.status_code == 200
    assert detail.json()["answer_sdp"] == answer
    assert detail.json()["answer_from"] == str(nurse.id)
    assert detail.json()["offer_sdp"] == offer


@pytest.mark.django_db
def test_webrtc_candidates_are_persisted_for_recovery():
    """ICE candidates are stored so the peer can connect after a missed realtime
    delivery, without relying on the live WebSocket frame."""
    doctor, nurse, _, _, _ = monitoring_context()
    doctor_client = APIClient()
    doctor_client.force_authenticate(doctor)
    created = doctor_client.post(
        reverse("calls:call-list"),
        {"recipient": str(nurse.id), "provider": "WEBRTC"},
        format="json",
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    candidate = {
        "candidate": "candidate:1 1 udp 2122260223 192.0.2.1 54321 typ host generation 0",
        "sdpMid": "0",
        "sdpMLineIndex": 0,
    }
    signaled = doctor_client.post(
        reverse("calls:call-signal", args=[session_id]),
        {
            "to_user": str(nurse.id),
            "data": {"type": "candidate", "candidate": candidate},
        },
        format="json",
    )
    assert signaled.status_code == 202

    nurse_client = APIClient()
    nurse_client.force_authenticate(nurse)
    detail = nurse_client.get(reverse("calls:call-detail", args=[session_id]))
    assert detail.status_code == 200
    assert detail.json()["ice_candidates"] == [
        {"from_user": str(doctor.id), "candidate": candidate}
    ]


@pytest.mark.django_db
def test_ice_config_reports_stun_and_configured_turn(monkeypatch):
    """The browser fetches STUN/TURN from the backend so deployments can enable
    TURN (required for cross-network calls) in the environment."""
    doctor, _, _, _, _ = monitoring_context()
    monkeypatch.setenv("WEBRTC_TURN_URLS", "turn:turn.example.test:3478")
    monkeypatch.setenv("WEBRTC_TURN_USERNAME", "velora-user")
    monkeypatch.setenv("WEBRTC_TURN_CREDENTIAL", "velora-secret")

    client = APIClient()
    client.force_authenticate(doctor)
    response = client.get(reverse("calls:call-ice"))
    assert response.status_code == 200

    servers = response.json()["iceServers"]
    assert any(
        "stun:stun.l.google.com:19302" in server["urls"] for server in servers
    )
    turn = next(server for server in servers if "turn:" in str(server["urls"]))
    assert "turn:turn.example.test:3478" in turn["urls"]
    assert turn["username"] == "velora-user"
    assert turn["credential"] == "velora-secret"


@pytest.mark.django_db
def test_simultaneous_calls_between_same_pair_are_serialized():
    """Two people calling each other at the same moment must not create two
    parallel sessions: the earlier session wins and the later caller gets a
    clear busy response (WhatsApp-style)."""
    doctor, nurse, _, _, _ = monitoring_context()
    doctor_client = APIClient()
    doctor_client.force_authenticate(doctor)
    created = doctor_client.post(
        reverse("calls:call-list"),
        {"recipient": str(nurse.id), "provider": "WEBRTC"},
        format="json",
    )
    assert created.status_code == 201

    # The nurse calls the doctor at the same time as the doctor called the nurse.
    nurse_client = APIClient()
    nurse_client.force_authenticate(nurse)
    rejected = nurse_client.post(
        reverse("calls:call-list"),
        {"recipient": str(doctor.id), "provider": "WEBRTC"},
        format="json",
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "call_busy"
    assert "calling you" in rejected.json()["error"]["message"]
    # Exactly one session exists between the pair.
    assert CallSession.objects.count() == 1


@pytest.mark.django_db
def test_caller_busy_when_already_in_another_call():
    """A user who is already in a call cannot place a second one."""
    doctor, nurse, guard, _, _ = monitoring_context()
    doctor_client = APIClient()
    doctor_client.force_authenticate(doctor)
    created = doctor_client.post(
        reverse("calls:call-list"),
        {"recipient": str(nurse.id), "provider": "WEBRTC"},
        format="json",
    )
    assert created.status_code == 201

    # The guard tries to call the doctor while the doctor is in a call.
    guard_client = APIClient()
    guard_client.force_authenticate(guard)
    rejected = guard_client.post(
        reverse("calls:call-list"),
        {"recipient": str(doctor.id), "provider": "WEBRTC"},
        format="json",
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "call_busy"
    assert "another call" in rejected.json()["error"]["message"]


@pytest.mark.django_db
def test_recipient_busy_when_in_another_call():
    """Calling someone who is already in a call reports them as busy."""
    doctor, nurse, guard, _, _ = monitoring_context()
    doctor_client = APIClient()
    doctor_client.force_authenticate(doctor)
    created = doctor_client.post(
        reverse("calls:call-list"),
        {"recipient": str(nurse.id), "provider": "WEBRTC"},
        format="json",
    )
    assert created.status_code == 201

    # The guard calls the nurse while the nurse is in a call with the doctor.
    guard_client = APIClient()
    guard_client.force_authenticate(guard)
    rejected = guard_client.post(
        reverse("calls:call-list"),
        {"recipient": str(nurse.id), "provider": "WEBRTC"},
        format="json",
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "call_busy"
    assert "currently in another call" in rejected.json()["error"]["message"]
    assert CallSession.objects.count() == 1


@pytest.mark.django_db
def test_busy_rule_relaxes_once_the_call_ends():
    """After the active call finishes, the same pair can call again."""
    doctor, nurse, _, _, _ = monitoring_context()
    doctor_client = APIClient()
    doctor_client.force_authenticate(doctor)
    created = doctor_client.post(
        reverse("calls:call-list"),
        {"recipient": str(nurse.id), "provider": "WEBRTC"},
        format="json",
    )
    session_id = created.json()["id"]
    doctor_client.post(
        reverse("calls:call-status", args=[session_id]),
        {"status": "COMPLETED"},
        format="json",
    )

    again = doctor_client.post(
        reverse("calls:call-list"),
        {"recipient": str(nurse.id), "provider": "WEBRTC"},
        format="json",
    )
    assert again.status_code == 201
    assert CallSession.objects.count() == 2


@pytest.mark.django_db
def test_missed_call_creates_persistent_notification_for_callee():
    """A call that is never answered leaves a 'Missed call' notification so the
    callee knows about it even if they were away from the app."""
    doctor, nurse, _, _, _ = monitoring_context()
    doctor_client = APIClient()
    doctor_client.force_authenticate(doctor)
    created = doctor_client.post(
        reverse("calls:call-list"),
        {"recipient": str(nurse.id), "provider": "WEBRTC"},
        format="json",
    )
    session_id = created.json()["id"]

    # The callee's app times out the unanswered ring.
    nurse_client = APIClient()
    nurse_client.force_authenticate(nurse)
    timed_out = nurse_client.post(
        reverse("calls:call-status", args=[session_id]),
        {"status": "NO_ANSWER"},
        format="json",
    )
    assert timed_out.status_code == 200

    notification = nurse.notifications.get(category="calls.missed")
    assert "Samuel" in notification.title or "Missed call" in notification.title
    assert notification.route == "/calls"
    assert notification.data["call_session_id"] == session_id

    # Repeating the transition must not duplicate the notification.
    nurse_client.post(
        reverse("calls:call-status", args=[session_id]),
        {"status": "NO_ANSWER"},
        format="json",
    )
    assert nurse.notifications.filter(category="calls.missed").count() == 1

    # The caller receives no missed-call notification, only the callee.
    assert doctor.notifications.filter(category="calls.missed").count() == 0


@pytest.mark.django_db
def test_stale_ringing_calls_expire_to_no_answer_on_list():
    """Calls that ring forever (callee app closed) are expired server-side and
    produce the missed-call notification."""
    doctor, nurse, _, _, _ = monitoring_context()
    doctor_client = APIClient()
    doctor_client.force_authenticate(doctor)
    created = doctor_client.post(
        reverse("calls:call-list"),
        {"recipient": str(nurse.id), "provider": "WEBRTC"},
        format="json",
    )
    session_id = created.json()["id"]
    CallSession.objects.filter(pk=session_id).update(
        initiated_at=timezone.now() - timedelta(minutes=5)
    )

    # Any participant listing calls triggers the expiry safety net.
    response = doctor_client.get(reverse("calls:call-list"))
    assert response.status_code == 200
    session = CallSession.objects.get(pk=session_id)
    assert session.status == CallSession.Status.NO_ANSWER
    assert session.ended_at is not None
    assert nurse.notifications.filter(category="calls.missed").exists()
