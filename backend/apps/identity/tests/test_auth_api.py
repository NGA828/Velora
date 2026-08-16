import pytest
from django.urls import reverse
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
