from pathlib import Path

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.hospital.models import ExternalHospital, ExternalHospitalSpecialty, Specialty
from apps.monitoring.tests.test_monitoring_workflow import monitoring_context
from apps.transfers.models import TransferRecommendation, TransferRequest, TransferTransmission


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_deterministic_recommendation_guard_approval_and_smtp_transmission(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    doctor, _, guard, profile, patient = monitoring_context()
    specialty = Specialty.objects.create(code="CARD", name="Cardiology")
    eligible = ExternalHospital.objects.create(
        name="Eligible Hospital",
        address="1 Referral Road",
        city="Yaoundé",
        country="CM",
        phone="+237600000201",
        transfer_email="transfer@eligible.example.org",
    )
    ExternalHospitalSpecialty.objects.create(
        external_hospital=eligible,
        specialty=specialty,
        availability_status="AVAILABLE",
    )
    ExternalHospital.objects.create(
        name="Missing Capability Hospital",
        address="2 Referral Road",
        city="Yaoundé",
        country="CM",
        phone="+237600000202",
        transfer_email="transfer@missing.example.org",
    )
    client = APIClient()
    client.force_authenticate(doctor)
    created = client.post(
        reverse("transfers:transfer-request-list"),
        {
            "patient": str(patient.id),
            "guardian": str(profile.id),
            "reason": "Specialist care required",
            "clinical_summary": "Approved transfer summary",
            "urgency": "URGENT",
            "requirements": [
                {
                    "requirement_type": "SPECIALTY",
                    "specialty": str(specialty.id),
                    "weight": "5.00",
                    "is_mandatory": True,
                }
            ],
        },
        format="json",
    )
    assert created.status_code == 201
    transfer_id = created.json()["id"]
    recommended = client.post(
        reverse("transfers:transfer-request-recommend", kwargs={"pk": transfer_id})
    )
    assert recommended.status_code == 200
    recommendations = recommended.json()["recommendations"]
    assert recommendations[0]["hospital_name"] == "Eligible Hospital"
    assert recommendations[0]["eligible"] is True
    assert recommendations[0]["score"] == "100.00"
    assert recommendations[1]["eligible"] is False
    assert TransferRecommendation.objects.count() == 2

    submitted = client.post(
        reverse("transfers:transfer-request-submit", kwargs={"pk": transfer_id}),
        {"hospital": str(eligible.id)},
        format="json",
    )
    assert submitted.json()["status"] == "PENDING_GUARDIAN"

    client.force_authenticate(guard)
    approved = client.post(
        reverse("transfers:transfer-request-decide", kwargs={"pk": transfer_id}),
        {"decision": "APPROVE", "reason": "Approved"},
        format="json",
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"

    client.force_authenticate(doctor)
    sent = client.post(
        reverse("transfers:transfer-request-send-package", kwargs={"pk": transfer_id})
    )
    assert sent.status_code == 200
    assert sent.json()["status"] == "FILE_SENT"
    transmission = TransferTransmission.objects.get()
    assert transmission.status == "SENT"
    assert len(transmission.checksum) == 64
    assert Path(tmp_path, transmission.package_storage_key).exists()
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["transfer@eligible.example.org"]
    assert mail.outbox[0].attachments[0][2] == "application/json"


@pytest.mark.django_db
def test_rejected_transfer_cannot_send_package():
    doctor, _, guard, profile, patient = monitoring_context()
    specialty = Specialty.objects.create(code="NEUR", name="Neurology")
    hospital = ExternalHospital.objects.create(
        name="Referral Hospital",
        address="1 Road",
        city="Yaoundé",
        country="CM",
        phone="+237600000203",
        transfer_email="transfer@referral.example.org",
    )
    ExternalHospitalSpecialty.objects.create(
        external_hospital=hospital,
        specialty=specialty,
    )
    client = APIClient()
    client.force_authenticate(doctor)
    transfer = client.post(
        reverse("transfers:transfer-request-list"),
        {
            "patient": str(patient.id),
            "guardian": str(profile.id),
            "reason": "Transfer review",
            "clinical_summary": "Summary",
            "urgency": "ROUTINE",
            "requirements": [
                {
                    "requirement_type": "SPECIALTY",
                    "specialty": str(specialty.id),
                    "weight": "1.00",
                    "is_mandatory": True,
                }
            ],
        },
        format="json",
    )
    transfer_id = transfer.json()["id"]
    client.post(reverse("transfers:transfer-request-recommend", kwargs={"pk": transfer_id}))
    client.post(
        reverse("transfers:transfer-request-submit", kwargs={"pk": transfer_id}),
        {"hospital": str(hospital.id)},
        format="json",
    )
    client.force_authenticate(guard)
    rejected = client.post(
        reverse("transfers:transfer-request-decide", kwargs={"pk": transfer_id}),
        {"decision": "REJECT", "reason": "Family declined"},
        format="json",
    )
    assert rejected.json()["status"] == "REJECTED"
    client.force_authenticate(doctor)
    blocked = client.post(
        reverse("transfers:transfer-request-send-package", kwargs={"pk": transfer_id})
    )
    assert blocked.status_code == 400
    assert TransferRequest.objects.get().status == "REJECTED"


@pytest.mark.django_db
def test_suggest_requirements_derives_conditions_and_specialties_from_medical_file():
    """The doctor can auto-suggest transfer requirements from the patient's
    medical file: active diagnoses contribute their condition plus the mapped
    specialties from the Head of Service catalogue."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.clinical_records.models import Diagnosis, MedicalFile
    from apps.hospital.models import ClinicalCondition, SpecialtyCondition

    doctor, _, guard, profile, patient = monitoring_context()
    specialty = Specialty.objects.create(code="CARD", name="Cardiology")
    condition = ClinicalCondition.objects.create(code="I25", name="Ischaemic heart disease")
    SpecialtyCondition.objects.create(
        specialty=specialty, condition=condition, match_weight="3.00"
    )
    # monitoring_context() registers the patient, which opens their medical file.
    assert MedicalFile.objects.filter(patient=patient).exists()
    Diagnosis.objects.create(
        patient=patient,
        condition=condition,
        code_snapshot="I25",
        name_snapshot="Ischaemic heart disease",
        status=Diagnosis.Status.CONFIRMED,
        diagnosed_at=timezone.now() - timedelta(days=2),
        diagnosed_by=doctor,
    )

    client = APIClient()
    client.force_authenticate(doctor)
    response = client.get(
        reverse("transfers:transfer-request-suggest-requirements"),
        {"patient": str(patient.id)},
    )
    assert response.status_code == 200
    suggestions = response.json()["suggestions"]
    types = {(item["requirement_type"], item["target"]) for item in suggestions}
    assert ("CONDITION", str(condition.id)) in types
    assert ("SPECIALTY", str(specialty.id)) in types
    by_type = {item["requirement_type"]: item for item in suggestions}
    assert by_type["SPECIALTY"]["weight"] == "3.00"
    assert by_type["CONDITION"]["label"] == "Ischaemic heart disease"
    assert "diagnosis" in by_type["CONDITION"]["source"].lower()

    # A Patient Guard cannot use the suggestion endpoint (doctor-only).
    guard_client = APIClient()
    guard_client.force_authenticate(guard)
    denied = guard_client.get(
        reverse("transfers:transfer-request-suggest-requirements"),
        {"patient": str(patient.id)},
    )
    assert denied.status_code == 403
