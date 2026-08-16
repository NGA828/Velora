import hashlib

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.hospital.models import Department
from apps.identity.models import Invitation, PatientGuardProfile, UserRole
from apps.identity.tests.factories import create_staff, create_user
from apps.monitoring.models import MonitoringResponse, MonitoringThread
from apps.patients.models import GuardianAccess, Patient
from apps.patients.tests.test_registration_workflow import registration_payload


def monitoring_context():
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
    patient = Patient.objects.get(pk=patient_response.json()["id"])
    guard = create_user(role=UserRole.PATIENT_GUARD, email="guard@example.org")
    profile = PatientGuardProfile.objects.create(user=guard)
    invitation = Invitation.objects.create(
        email=guard.email,
        intended_role=UserRole.PATIENT_GUARD,
        token_hash=hashlib.sha256(b"monitoring-guard").hexdigest(),
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
    return doctor, nurse, guard, profile, patient


@pytest.mark.django_db
def test_doctor_question_guard_response_and_revision_history():
    doctor, _, guard, profile, patient = monitoring_context()
    client = APIClient()
    client.force_authenticate(doctor)
    created = client.post(
        reverse("monitoring:monitoring-thread-list"),
        {"patient": str(patient.id), "guardian": str(profile.id), "subject": "Pain review"},
        format="json",
    )
    assert created.status_code == 201
    thread_id = created.json()["id"]
    question = client.post(
        reverse("monitoring:monitoring-thread-add-question", kwargs={"pk": thread_id}),
        {
            "prompt": "Has the patient experienced increased pain?",
            "response_type": "BOOLEAN",
            "options": [],
        },
        format="json",
    )
    assert question.status_code == 200
    question_id = question.json()["questions"][0]["id"]

    client.force_authenticate(guard)
    first = client.post(
        reverse(
            "monitoring:monitoring-thread-answer",
            kwargs={"pk": thread_id, "question_id": question_id},
        ),
        {"answer": True},
        format="json",
    )
    assert first.status_code == 200
    assert first.json()["questions"][0]["current_response"]["answer"] is True
    revised = client.post(
        reverse(
            "monitoring:monitoring-thread-answer",
            kwargs={"pk": thread_id, "question_id": question_id},
        ),
        {"answer": False},
        format="json",
    )
    assert revised.status_code == 200
    assert MonitoringResponse.objects.count() == 2
    assert MonitoringResponse.objects.filter(is_current=True, answer=False).exists()
    assert MonitoringResponse.objects.filter(is_current=False, answer=True).exists()

    client.force_authenticate(doctor)
    detail = client.get(reverse("monitoring:monitoring-thread-detail", kwargs={"pk": thread_id}))
    assert detail.json()["questions"][0]["current_response"]["answer"] is False


@pytest.mark.django_db
def test_guard_cannot_answer_another_guards_thread():
    doctor, _, _, profile, patient = monitoring_context()
    other_guard = create_user(
        role=UserRole.PATIENT_GUARD,
        email="other.guard@example.org",
    )
    PatientGuardProfile.objects.create(user=other_guard)
    client = APIClient()
    client.force_authenticate(doctor)
    thread = client.post(
        reverse("monitoring:monitoring-thread-list"),
        {"patient": str(patient.id), "guardian": str(profile.id), "subject": "Review"},
        format="json",
    )
    client.post(
        reverse(
            "monitoring:monitoring-thread-add-question",
            kwargs={"pk": thread.json()["id"]},
        ),
        {"prompt": "Describe symptoms", "response_type": "TEXT"},
        format="json",
    )
    question_id = MonitoringThread.objects.get().questions.get().id

    client.force_authenticate(other_guard)
    response = client.post(
        reverse(
            "monitoring:monitoring-thread-answer",
            kwargs={"pk": thread.json()["id"], "question_id": question_id},
        ),
        {"answer": "Unauthorized"},
        format="json",
    )
    assert response.status_code == 404
