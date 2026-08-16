import re

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.hospital.models import Department
from apps.identity.models import User, UserRole
from apps.identity.tests.factories import create_staff
from apps.patients.models import GuardianAccess
from apps.patients.tests.test_registration_workflow import registration_payload


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_nurse_invites_guard_and_acceptance_activates_only_linked_patient_access(
    django_capture_on_commit_callbacks,
):
    department = Department.objects.create(code="MED", name="Medicine")
    doctor, _ = create_staff(
        role=UserRole.DOCTOR, email="doctor@example.org", employee_number="DOC-001"
    )
    nurse, nurse_profile = create_staff(
        role=UserRole.NURSE, email="nurse@example.org", employee_number="NUR-001"
    )
    client = APIClient()
    client.force_authenticate(doctor)
    patient_response = client.post(
        reverse("patients:patient-list"),
        registration_payload(nurse_profile.id, department.id),
        format="json",
    )
    patient_id = patient_response.json()["id"]

    client.force_authenticate(nurse)
    with django_capture_on_commit_callbacks(execute=True):
        invite = client.post(
            reverse("patients:patient-guardians", kwargs={"pk": patient_id}),
            {
                "email": "guard@example.org",
                "relationship": "Sibling",
                "can_view_medical_file": True,
                "can_answer_monitoring": True,
                "can_decide_transfers": True,
                "can_view_billing": False,
            },
            format="json",
        )
    assert invite.status_code == 201
    assert invite.json()["status"] == "INVITED"
    token = re.search(r"#token=([^\s]+)", mail.outbox[-1].body).group(1)

    anonymous = APIClient(enforce_csrf_checks=True)
    csrf_response = anonymous.get(reverse("identity:csrf"))
    csrf_token = csrf_response.json()["csrf_token"]
    accepted = anonymous.post(
        reverse("identity:accept-invitation"),
        {
            "token": token,
            "first_name": "Jean",
            "last_name": "Nkoa",
            "phone": "+237600100102",
            "password": "Guardian-passphrase-927!",
            "confirm_password": "Guardian-passphrase-927!",
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert accepted.status_code == 201
    access = GuardianAccess.objects.get()
    assert access.status == GuardianAccess.Status.ACTIVE
    assert access.guardian.user.email == "guard@example.org"

    guard = User.objects.get(email="guard@example.org")
    guard_client = APIClient()
    guard_client.force_authenticate(guard)
    patients = guard_client.get(reverse("patients:patient-list"))
    file_list = guard_client.get(reverse("clinical_records:medical-file-list"))
    assert patients.json()["pagination"]["count"] == 1
    assert patients.json()["data"][0]["id"] == patient_id
    assert file_list.json()["pagination"]["count"] == 1


@pytest.mark.django_db
def test_unassigned_nurse_cannot_invite_guard():
    department = Department.objects.create(code="MED", name="Medicine")
    doctor, _ = create_staff(
        role=UserRole.DOCTOR, email="doctor@example.org", employee_number="DOC-001"
    )
    _, assigned_profile = create_staff(
        role=UserRole.NURSE, email="assigned@example.org", employee_number="NUR-001"
    )
    unrelated, _ = create_staff(
        role=UserRole.NURSE, email="unrelated@example.org", employee_number="NUR-002"
    )
    client = APIClient()
    client.force_authenticate(doctor)
    patient = client.post(
        reverse("patients:patient-list"),
        registration_payload(assigned_profile.id, department.id),
        format="json",
    )

    client.force_authenticate(unrelated)
    response = client.post(
        reverse("patients:patient-guardians", kwargs={"pk": patient.json()["id"]}),
        {"email": "guard@example.org", "relationship": "Parent"},
        format="json",
    )

    assert response.status_code == 404
    assert GuardianAccess.objects.count() == 0
