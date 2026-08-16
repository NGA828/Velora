import hashlib

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import MedicalRecordAccess
from apps.clinical_records.models import ClinicalNote, Diagnosis
from apps.hospital.models import ClinicalCondition, Department
from apps.identity.models import Invitation, PatientGuardProfile, UserRole
from apps.identity.tests.factories import create_staff, create_user
from apps.patients.models import GuardianAccess, Patient
from apps.patients.tests.test_registration_workflow import registration_payload


def care_context():
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
    return doctor, nurse, patient, patient.care_episodes.get(status="ACTIVE")


@pytest.mark.django_db
def test_only_assigned_doctor_can_record_diagnosis():
    doctor, nurse, patient, episode = care_context()
    condition = ClinicalCondition.objects.create(
        coding_system="LOCAL", code="C-1", name="Approved local condition"
    )
    payload = {
        "patient": str(patient.id),
        "care_episode": str(episode.id),
        "condition": str(condition.id),
        "description": "Clinical description",
        "status": "CONFIRMED",
        "guardian_visibility": "INTERNAL",
    }
    client = APIClient()
    client.force_authenticate(nurse)
    assert (
        client.post(reverse("clinical_records:diagnosis-list"), payload, format="json").status_code
        == 403
    )

    client.force_authenticate(doctor)
    created = client.post(reverse("clinical_records:diagnosis-list"), payload, format="json")
    assert created.status_code == 201
    diagnosis = Diagnosis.objects.get()
    assert diagnosis.name_snapshot == condition.name
    assert diagnosis.code_snapshot == "LOCAL:C-1"


@pytest.mark.django_db
def test_nurse_can_write_only_nursing_notes_and_signed_notes_are_immutable():
    _, nurse, patient, episode = care_context()
    client = APIClient()
    client.force_authenticate(nurse)
    base = {
        "patient": str(patient.id),
        "care_episode": str(episode.id),
        "title": "Care observation",
        "body": "Authorized nursing observation.",
        "guardian_visibility": "INTERNAL",
    }
    forbidden = client.post(
        reverse("clinical_records:clinical-note-list"),
        {**base, "note_type": "PROGRESS"},
        format="json",
    )
    assert forbidden.status_code == 403

    created = client.post(
        reverse("clinical_records:clinical-note-list"),
        {**base, "note_type": "NURSING"},
        format="json",
    )
    assert created.status_code == 201
    signed = client.post(
        reverse("clinical_records:clinical-note-sign", kwargs={"pk": created.json()["id"]})
    )
    assert signed.status_code == 200
    assert signed.json()["status"] == ClinicalNote.Status.SIGNED
    edited = client.patch(
        reverse("clinical_records:clinical-note-detail", kwargs={"pk": created.json()["id"]}),
        {"body": "Silent rewrite"},
        format="json",
    )
    assert edited.status_code == 400


@pytest.mark.django_db
def test_guard_sees_only_released_signed_records():
    doctor, _, patient, episode = care_context()
    guard = create_user(
        role=UserRole.PATIENT_GUARD,
        email="guard@example.org",
    )
    guard_profile = PatientGuardProfile.objects.create(user=guard)
    invitation = Invitation.objects.create(
        email=guard.email,
        intended_role=UserRole.PATIENT_GUARD,
        token_hash=hashlib.sha256(b"accepted").hexdigest(),
        expires_at=timezone.now(),
        accepted_at=timezone.now(),
        invited_by=doctor,
    )
    access = GuardianAccess.objects.create(
        patient=patient,
        guardian=guard_profile,
        invitation=invitation,
        relationship="Parent",
        status=GuardianAccess.Status.ACTIVE,
        granted_by=doctor,
        granted_at=timezone.now(),
    )
    ClinicalNote.objects.create(
        patient=patient,
        care_episode=episode,
        note_type="PROGRESS",
        title="Internal note",
        body="Not released",
        status="SIGNED",
        signed_at=timezone.now(),
        author=doctor,
        guardian_visibility="INTERNAL",
    )
    released = ClinicalNote.objects.create(
        patient=patient,
        care_episode=episode,
        note_type="PROGRESS",
        title="Released update",
        body="Released information",
        status="SIGNED",
        signed_at=timezone.now(),
        author=doctor,
        guardian_visibility="GUARDIAN",
    )
    client = APIClient()
    client.force_authenticate(guard)

    response = client.get(
        reverse("clinical_records:clinical-note-list"), {"patient": str(patient.id)}
    )

    assert response.status_code == 200
    assert response.json()["pagination"]["count"] == 1
    assert response.json()["data"][0]["id"] == str(released.id)
    assert MedicalRecordAccess.objects.filter(
        user=guard,
        patient=patient,
        object_type="clinical_records.ClinicalNote",
        action="LIST",
    ).exists()

    access.can_view_medical_file = False
    access.save(update_fields=["can_view_medical_file", "updated_at"])
    restricted = client.get(
        reverse("clinical_records:clinical-note-list"), {"patient": str(patient.id)}
    )
    assert restricted.json()["pagination"]["count"] == 0
