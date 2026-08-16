import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.identity.models import Invitation, StaffProfile, UserRole
from apps.identity.services import create_invitation
from apps.identity.tests.factories import create_staff


@pytest.mark.django_db
def test_nurse_cannot_access_staff_directory():
    nurse, _ = create_staff(role=UserRole.NURSE)
    client = APIClient()
    client.force_authenticate(nurse)

    response = client.get(reverse("identity:staff-list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_head_of_service_can_only_invite_doctor_or_nurse():
    head, _ = create_staff(
        role=UserRole.HEAD_OF_SERVICE,
        email="head@example.org",
        employee_number="HOS-001",
    )
    client = APIClient()
    client.force_authenticate(head)

    rejected = client.post(
        reverse("identity:staff-invitations"),
        {
            "email": "accounts@example.org",
            "intended_role": UserRole.ACCOUNTING,
            "employee_number": "ACC-001",
        },
        format="json",
    )
    assert rejected.status_code == 400
    assert Invitation.objects.count() == 0

    accepted = client.post(
        reverse("identity:staff-invitations"),
        {
            "email": "doctor.new@example.org",
            "intended_role": UserRole.DOCTOR,
            "employee_number": "DOC-001",
            "job_title": "Medical Officer",
        },
        format="json",
    )
    assert accepted.status_code == 201
    assert "token" not in accepted.json()
    assert Invitation.objects.filter(email="doctor.new@example.org").exists()


@pytest.mark.django_db
def test_head_of_service_can_deactivate_clinical_staff_without_deleting_history():
    head, _ = create_staff(
        role=UserRole.HEAD_OF_SERVICE,
        email="head@example.org",
        employee_number="HOS-001",
    )
    doctor, profile = create_staff(
        role=UserRole.DOCTOR,
        email="doctor@example.org",
        employee_number="DOC-001",
    )
    client = APIClient()
    client.force_authenticate(head)

    response = client.patch(
        reverse("identity:staff-detail", kwargs={"pk": profile.id}),
        {"employment_status": "INACTIVE", "account_active": False},
        format="json",
    )

    assert response.status_code == 200
    doctor.refresh_from_db()
    profile.refresh_from_db()
    assert doctor.is_active is False
    assert profile.employment_status == "INACTIVE"


@pytest.mark.django_db
def test_guard_cannot_guess_or_revoke_staff_invitation():
    head, _ = create_staff(role=UserRole.HEAD_OF_SERVICE, email="head@example.org")
    invitation, _ = create_invitation(
        inviter=head,
        email="doctor.new@example.org",
        intended_role=UserRole.DOCTOR,
        context={"employee_number": "DOC-001"},
    )
    guard, _ = create_staff(role=UserRole.NURSE, email="other@example.org")
    client = APIClient()
    client.force_authenticate(guard)

    response = client.post(
        reverse("identity:revoke-invitation", kwargs={"invitation_id": invitation.id})
    )

    assert response.status_code == 403
    invitation.refresh_from_db()
    assert invitation.revoked_at is None


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_invitation_acceptance_creates_correct_staff_profile_and_session():
    head, _ = create_staff(
        role=UserRole.HEAD_OF_SERVICE,
        email="head@example.org",
        employee_number="HOS-001",
    )
    invitation, raw_token = create_invitation(
        inviter=head,
        email="doctor.new@example.org",
        intended_role=UserRole.DOCTOR,
        context={
            "employee_number": "DOC-002",
            "job_title": "Doctor",
            "license_number": "LIC-77",
        },
    )
    client = APIClient(enforce_csrf_checks=True)
    csrf_response = client.get(reverse("identity:csrf"))
    csrf_token = csrf_response.cookies["velora_csrftoken"].value

    response = client.post(
        reverse("identity:accept-invitation"),
        {
            "token": raw_token,
            "first_name": "Amara",
            "last_name": "Nwosu",
            "phone": "+237600000000",
            "password": "Accepted-passphrase-927!",
            "confirm_password": "Accepted-passphrase-927!",
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201
    assert response.json()["user"]["role"] == UserRole.DOCTOR
    profile = StaffProfile.objects.get(user__email="doctor.new@example.org")
    assert profile.employee_number == "DOC-002"
    assert profile.license_number == "LIC-77"
    invitation.refresh_from_db()
    assert invitation.accepted_at is not None
    assert client.get(reverse("identity:session")).status_code == 200

    rotated_csrf_token = client.cookies["velora_csrftoken"].value
    second_attempt = client.post(
        reverse("identity:accept-invitation"),
        {
            "token": raw_token,
            "first_name": "Amara",
            "last_name": "Nwosu",
            "password": "Accepted-passphrase-927!",
            "confirm_password": "Accepted-passphrase-927!",
        },
        format="json",
        HTTP_X_CSRFTOKEN=rotated_csrf_token,
    )
    assert second_attempt.status_code == 400
