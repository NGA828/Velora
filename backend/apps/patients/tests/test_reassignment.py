import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.hospital.models import Department
from apps.identity.models import UserRole
from apps.identity.tests.factories import create_staff
from apps.patients.models import PatientCareAssignment
from apps.patients.tests.test_registration_workflow import registration_payload


@pytest.mark.django_db
def test_assigned_doctor_can_reassign_nurse_and_old_nurse_loses_access():
    department = Department.objects.create(code="MED", name="Medicine")
    doctor, _ = create_staff(
        role=UserRole.DOCTOR, email="doctor@example.org", employee_number="DOC-001"
    )
    old_nurse, old_profile = create_staff(
        role=UserRole.NURSE, email="old@example.org", employee_number="NUR-001"
    )
    new_nurse, new_profile = create_staff(
        role=UserRole.NURSE, email="new@example.org", employee_number="NUR-002"
    )
    client = APIClient()
    client.force_authenticate(doctor)
    patient = client.post(
        reverse("patients:patient-list"),
        registration_payload(old_profile.id, department.id),
        format="json",
    )
    patient_id = patient.json()["id"]

    reassigned = client.post(
        reverse("patients:patient-assign-nurse", kwargs={"pk": patient_id}),
        {"nurse": str(new_profile.id)},
        format="json",
    )
    assert reassigned.status_code == 200
    assert reassigned.json()["primary_nurse"]["staff_id"] == str(new_profile.id)

    client.force_authenticate(old_nurse)
    assert (
        client.get(reverse("patients:patient-detail", kwargs={"pk": patient_id})).status_code == 404
    )
    client.force_authenticate(new_nurse)
    assert (
        client.get(reverse("patients:patient-detail", kwargs={"pk": patient_id})).status_code == 200
    )
    assert PatientCareAssignment.objects.filter(
        patient_id=patient_id, staff=old_profile, ends_at__isnull=False
    ).exists()
