import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.identity.models import LoginEvent, LoginOutcome, UserRole
from apps.identity.tests.factories import DEFAULT_PASSWORD, create_staff


def csrf_client() -> tuple[APIClient, str]:
    client = APIClient(enforce_csrf_checks=True)
    response = client.get(reverse("identity:csrf"))
    return client, response.cookies["velora_csrftoken"].value


@pytest.mark.django_db
def test_login_requires_csrf_and_creates_a_server_session():
    user, _ = create_staff(role=UserRole.DOCTOR, email="doctor@example.org")
    client = APIClient(enforce_csrf_checks=True)

    rejected = client.post(
        reverse("identity:login"),
        {"email": user.email, "password": DEFAULT_PASSWORD},
        format="json",
    )
    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "csrf_failed"

    client, csrf_token = csrf_client()
    response = client.post(
        reverse("identity:login"),
        {"email": user.email, "password": DEFAULT_PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == UserRole.DOCTOR
    assert "patients.register" in response.json()["user"]["capabilities"]
    assert "velora_session" in response.cookies
    assert LoginEvent.objects.filter(user=user, outcome=LoginOutcome.SUCCESS).exists()
    assert AuditEvent.objects.filter(action="identity.session.started", actor=user).exists()

    session = client.get(reverse("identity:session"))
    assert session.status_code == 200
    assert session.json()["user"]["email"] == user.email


@pytest.mark.django_db
def test_invalid_login_is_unauthorized_and_does_not_reveal_account_state():
    create_staff(role=UserRole.NURSE, email="nurse@example.org")
    client, csrf_token = csrf_client()

    response = client.post(
        reverse("identity:login"),
        {"email": "nurse@example.org", "password": "incorrect"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "The email or password is incorrect."
    assert response["X-Request-ID"]
    assert LoginEvent.objects.filter(outcome=LoginOutcome.INVALID_CREDENTIALS).exists()


@pytest.mark.django_db
def test_temporary_password_blocks_other_api_capabilities():
    user, _ = create_staff(
        role=UserRole.HEAD_OF_SERVICE,
        email="temporary@example.org",
        must_change_password=True,
    )
    client = APIClient()
    client.force_login(user)

    blocked = client.get(reverse("identity:staff-list"))
    session = client.get(reverse("identity:session"))

    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "password_change_required"
    assert session.status_code == 200


@pytest.mark.django_db
def test_password_change_keeps_session_and_records_audit():
    user, _ = create_staff(role=UserRole.NURSE, email="nurse@example.org")
    client, csrf_token = csrf_client()
    client.post(
        reverse("identity:login"),
        {"email": user.email, "password": DEFAULT_PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    rotated_csrf_token = client.cookies["velora_csrftoken"].value
    response = client.post(
        reverse("identity:change-password"),
        {
            "old_password": DEFAULT_PASSWORD,
            "new_password": "A-new-foundation-passphrase-928!",
            "confirm_password": "A-new-foundation-passphrase-928!",
        },
        format="json",
        HTTP_X_CSRFTOKEN=rotated_csrf_token,
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password("A-new-foundation-passphrase-928!")
    assert client.get(reverse("identity:session")).status_code == 200
    assert AuditEvent.objects.filter(action="identity.password.changed", actor=user).exists()


@pytest.mark.django_db
def test_me_endpoint_updates_profile_and_avatar(monkeypatch, tmp_path):
    from apps.identity.tests.factories import create_user

    user = create_user(email="profile@example.org")
    client = APIClient()
    client.force_authenticate(user)

    # Update name and phone without touching the avatar.
    updated = client.patch(
        reverse("identity:me"),
        {"first_name": "Amara", "last_name": "Nwosu", "phone": "+237699000000"},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.json()["user"]["first_name"] == "Amara"
    assert updated.json()["user"]["last_name"] == "Nwosu"
    assert updated.json()["user"]["phone"] == "+237699000000"
    user.refresh_from_db()
    assert user.first_name == "Amara"
    assert user.phone == "+237699000000"

    # Upload a small PNG avatar (multipart).
    import io
    import struct
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color=(20, 40, 80)).save(buffer, format="PNG")
    buffer.seek(0)
    avatar = SimpleUploadedFile(
        "profile.png", buffer.read(), content_type="image/png"
    )
    uploaded = client.patch(
        reverse("identity:me"),
        {"avatar": avatar},
        format="multipart",
    )
    assert uploaded.status_code == 200
    user.refresh_from_db()
    assert user.avatar.name.startswith("avatars/")
    assert uploaded.json()["user"]["avatar_url"] == reverse("identity:my-avatar")

    # The avatar is served through the authenticated endpoint.
    served = client.get(reverse("identity:my-avatar"))
    assert served.status_code == 200
    assert served["Content-Type"] == "image/png"

    # A different user cannot read this avatar.
    other = create_user(email="other-profile@example.org")
    other_client = APIClient()
    other_client.force_authenticate(other)
    assert other_client.get(reverse("identity:my-avatar")).status_code == 404


@pytest.mark.django_db
def test_me_endpoint_rejects_blank_name_and_bad_avatar_type():
    from apps.identity.tests.factories import create_user

    user = create_user(email="profile2@example.org")
    client = APIClient()
    client.force_authenticate(user)

    blank = client.patch(
        reverse("identity:me"), {"first_name": "   "}, format="json"
    )
    assert blank.status_code == 400

    bad = client.patch(
        reverse("identity:me"),
        {"avatar": SimpleUploadedFile("x.txt", b"not-an-image", content_type="text/plain")},
        format="multipart",
    )
    assert bad.status_code == 400
