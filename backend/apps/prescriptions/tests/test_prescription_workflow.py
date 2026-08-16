import hashlib
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.hospital.models import Department
from apps.identity.models import Invitation, PatientGuardProfile, UserRole
from apps.identity.tests.factories import create_staff, create_user
from apps.patients.models import GuardianAccess, Patient
from apps.patients.tests.test_registration_workflow import registration_payload
from apps.prescriptions.models import Medication, MedicationDose, Prescription


def prescription_context(with_guard=False):
    department = Department.objects.create(code="MED", name="Medicine")
    doctor, _ = create_staff(
        role=UserRole.DOCTOR, email="doctor@example.org", employee_number="DOC-001"
    )
    nurse, nurse_profile = create_staff(
        role=UserRole.NURSE, email="nurse@example.org", employee_number="NUR-001"
    )
    client = APIClient()
    client.force_authenticate(doctor)
    response = client.post(
        reverse("patients:patient-list"),
        registration_payload(nurse_profile.id, department.id),
        format="json",
    )
    patient = Patient.objects.get(pk=response.json()["id"])
    guard = None
    if with_guard:
        guard = create_user(role=UserRole.PATIENT_GUARD, email="guard@example.org")
        profile = PatientGuardProfile.objects.create(user=guard)
        invitation = Invitation.objects.create(
            email=guard.email,
            intended_role=UserRole.PATIENT_GUARD,
            token_hash=hashlib.sha256(b"accepted-prescription").hexdigest(),
            expires_at=timezone.now(),
            accepted_at=timezone.now(),
            invited_by=nurse,
        )
        GuardianAccess.objects.create(
            patient=patient,
            guardian=profile,
            invitation=invitation,
            relationship="Parent",
            status="ACTIVE",
            granted_by=nurse,
            granted_at=timezone.now(),
        )
    medication = Medication.objects.create(
        generic_name="Configured medicine",
        form="Tablet",
        strength="10 mg",
    )
    return doctor, nurse, guard, patient, medication


def prescription_payload(patient, medication, days=2):
    start = timezone.localdate()
    return {
        "patient": str(patient.id),
        "starts_on": start.isoformat(),
        "ends_on": (start + timedelta(days=days - 1)).isoformat(),
        "clinical_instructions": "Configured instructions",
        "items": [
            {
                "medication": str(medication.id),
                "dose_amount": "1",
                "dose_unit": "tablet",
                "route": "ORAL",
                "frequency_display": "Once daily",
                "duration_days": days,
                "instructions": "Take as directed",
                "schedule_type": "SCHEDULED",
                "schedule_times": [{"local_time": "08:00", "days_of_week": []}],
            }
        ],
    }


@pytest.mark.django_db
def test_doctor_creates_and_activates_schedule_with_concrete_doses():
    doctor, nurse, _, patient, medication = prescription_context()
    client = APIClient()
    client.force_authenticate(doctor)

    created = client.post(
        reverse("prescriptions:prescription-list"),
        prescription_payload(patient, medication),
        format="json",
    )
    assert created.status_code == 201
    assert created.json()["status"] == Prescription.Status.DRAFT
    assert MedicationDose.objects.count() == 0

    activated = client.post(
        reverse("prescriptions:prescription-activate", kwargs={"pk": created.json()["id"]})
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == Prescription.Status.ACTIVE
    assert MedicationDose.objects.count() == 2
    assert activated.json()["dose_summary"]["PENDING"] == 2

    client.force_authenticate(nurse)
    visible = client.get(reverse("prescriptions:prescription-list"), {"patient": str(patient.id)})
    assert visible.status_code == 200
    assert visible.json()["pagination"]["count"] == 1


@pytest.mark.django_db
def test_patient_guard_sees_only_activated_prescriptions():
    doctor, _, guard, patient, medication = prescription_context(with_guard=True)
    client = APIClient()
    client.force_authenticate(doctor)
    created = client.post(
        reverse("prescriptions:prescription-list"),
        prescription_payload(patient, medication, days=1),
        format="json",
    )

    client.force_authenticate(guard)
    hidden = client.get(reverse("prescriptions:prescription-list"))
    assert hidden.json()["pagination"]["count"] == 0

    client.force_authenticate(doctor)
    client.post(reverse("prescriptions:prescription-activate", kwargs={"pk": created.json()["id"]}))
    client.force_authenticate(guard)
    visible = client.get(reverse("prescriptions:prescription-list"))
    assert visible.json()["pagination"]["count"] == 1
    assert visible.json()["data"][0]["items"][0]["medication_name"].startswith(
        "Configured medicine"
    )


@pytest.mark.django_db
def test_invalid_schedule_is_rejected_without_partial_prescription():
    doctor, _, _, patient, medication = prescription_context()
    payload = prescription_payload(patient, medication)
    payload["items"][0]["schedule_times"] = []
    client = APIClient()
    client.force_authenticate(doctor)

    response = client.post(reverse("prescriptions:prescription-list"), payload, format="json")

    assert response.status_code == 400
    assert Prescription.objects.count() == 0
