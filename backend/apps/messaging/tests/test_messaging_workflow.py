import uuid

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from apps.identity.models import UserRole
from apps.identity.tests.factories import create_staff
from apps.messaging.models import Message, MessageReceipt
from apps.messaging.realtime import publish_user_event, user_group
from apps.monitoring.tests.test_monitoring_workflow import monitoring_context


def test_realtime_user_event_is_published_to_authenticated_user_group():
    layer = get_channel_layer()
    channel = async_to_sync(layer.new_channel)()
    async_to_sync(layer.group_add)(user_group("00000000-0000-0000-0000-000000000001"), channel)

    publish_user_event(
        user_id="00000000-0000-0000-0000-000000000001",
        event_type="message.created",
        payload={"conversation_id": "one"},
    )
    event = async_to_sync(layer.receive)(channel)

    assert event["type"] == "user.event"
    assert event["event_type"] == "message.created"
    assert event["payload"]["conversation_id"] == "one"


@pytest.mark.django_db
def test_bidirectional_message_receipts_move_sent_delivered_seen():
    doctor, _, guard, _, patient = monitoring_context()
    client = APIClient()
    client.force_authenticate(doctor)
    conversation = client.post(
        reverse("messaging:conversation-list"),
        {
            "participant": str(guard.id),
            "patient": str(patient.id),
            "subject": "Care coordination",
        },
        format="json",
    )
    assert conversation.status_code == 201
    conversation_id = conversation.json()["id"]
    client_id = str(uuid.uuid4())
    sent = client.post(
        reverse("messaging:conversation-messages", kwargs={"pk": conversation_id}),
        {"body": "Please review the monitoring question.", "client_message_id": client_id},
        format="json",
    )
    assert sent.status_code == 201
    assert sent.json()["delivery_state"] == "SENT"
    message_id = sent.json()["id"]
    assert MessageReceipt.objects.filter(message_id=message_id, recipient=guard).exists()

    duplicate = client.post(
        reverse("messaging:conversation-messages", kwargs={"pk": conversation_id}),
        {"body": "Duplicate retry", "client_message_id": client_id},
        format="json",
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == message_id
    assert Message.objects.count() == 1

    client.force_authenticate(guard)
    inbox = client.get(reverse("messaging:conversation-messages", kwargs={"pk": conversation_id}))
    assert inbox.status_code == 200
    assert inbox.json()["data"][0]["body"] == "Please review the monitoring question."
    delivered = client.post(
        reverse("messaging:conversation-delivered", kwargs={"pk": conversation_id}),
        {"up_to_message": message_id},
        format="json",
    )
    assert delivered.status_code == 200

    client.force_authenticate(doctor)
    after_delivery = client.get(
        reverse("messaging:conversation-messages", kwargs={"pk": conversation_id})
    )
    assert after_delivery.json()["data"][0]["delivery_state"] == "DELIVERED"

    client.force_authenticate(guard)
    seen = client.post(
        reverse("messaging:conversation-seen", kwargs={"pk": conversation_id}),
        {"up_to_message": message_id},
        format="json",
    )
    assert seen.status_code == 200
    client.force_authenticate(doctor)
    after_seen = client.get(
        reverse("messaging:conversation-messages", kwargs={"pk": conversation_id})
    )
    assert after_seen.json()["data"][0]["delivery_state"] == "SEEN"


@pytest.mark.django_db
def test_unrelated_user_cannot_guess_conversation_or_patient_context():
    doctor, _, guard, _, patient = monitoring_context()
    unrelated, _ = create_staff(
        role=UserRole.DOCTOR,
        email="unrelated@example.org",
        employee_number="DOC-009",
    )
    client = APIClient()
    client.force_authenticate(doctor)
    conversation = client.post(
        reverse("messaging:conversation-list"),
        {"participant": str(guard.id), "patient": str(patient.id)},
        format="json",
    )
    client.force_authenticate(unrelated)
    assert (
        client.get(
            reverse("messaging:conversation-detail", kwargs={"pk": conversation.json()["id"]})
        ).status_code
        == 404
    )
    forbidden = client.post(
        reverse("messaging:conversation-list"),
        {"participant": str(guard.id), "patient": str(patient.id)},
        format="json",
    )
    assert forbidden.status_code == 404


@pytest.mark.django_db
def test_attachment_is_restricted_to_conversation_participants(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    doctor, nurse, guard, _, patient = monitoring_context()
    client = APIClient()
    client.force_authenticate(doctor)
    conversation = client.post(
        reverse("messaging:conversation-list"),
        {"participant": str(guard.id), "patient": str(patient.id)},
        format="json",
    )
    conversation_id = conversation.json()["id"]
    upload = SimpleUploadedFile(
        "care-note.txt",
        b"Authorized attachment content",
        content_type="text/plain",
    )
    sent = client.post(
        reverse("messaging:conversation-messages", kwargs={"pk": conversation_id}),
        {
            "body": "Attached document",
            "client_message_id": str(uuid.uuid4()),
            "attachment": upload,
        },
        format="multipart",
    )
    assert sent.status_code == 201
    attachment = sent.json()["attachment"]

    disguised = SimpleUploadedFile(
        "disguised.pdf",
        b"not a real PDF",
        content_type="application/pdf",
    )
    rejected = client.post(
        reverse("messaging:conversation-messages", kwargs={"pk": conversation_id}),
        {
            "body": "Unsafe upload",
            "client_message_id": str(uuid.uuid4()),
            "attachment": disguised,
        },
        format="multipart",
    )
    assert rejected.status_code == 400

    client.force_authenticate(guard)
    download = client.get(attachment["download_url"], HTTP_HOST="testserver")
    assert download.status_code == 200
    assert download["Content-Disposition"].startswith("attachment;")

    client.force_authenticate(nurse)
    denied = client.get(attachment["download_url"], HTTP_HOST="testserver")
    assert denied.status_code == 404
