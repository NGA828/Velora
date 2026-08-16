from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import MedicalRecordAccess
from apps.death_certificates.models import DeathCertificate
from apps.monitoring.tests.test_monitoring_workflow import monitoring_context
from apps.patients.models import Patient


@pytest.mark.django_db
def test_doctor_issues_guard_views_and_prints_certificate():
    doctor, _, guard, _, patient = monitoring_context()
    client = APIClient()
    client.force_authenticate(doctor)
    created = client.post(
        reverse("death_certificates:death-certificate-list"),
        {
            "patient": str(patient.id),
            "death_datetime": (timezone.now() - timedelta(hours=1)).isoformat(),
            "place_of_death": "Velora Central Hospital",
            "primary_cause": "Clinically certified cause",
            "contributing_causes": "",
            "manner_of_death": "Natural",
            "notes": "Certificate test",
        },
        format="json",
    )
    assert created.status_code == 201
    certificate_id = created.json()["id"]

    client.force_authenticate(guard)
    hidden = client.get(reverse("death_certificates:death-certificate-list"))
    assert hidden.json()["pagination"]["count"] == 0

    client.force_authenticate(doctor)
    issued = client.post(
        reverse(
            "death_certificates:death-certificate-issue",
            kwargs={"pk": certificate_id},
        )
    )
    assert issued.status_code == 200
    assert issued.json()["status"] == DeathCertificate.Status.ISSUED
    patient.refresh_from_db()
    assert patient.status == Patient.Status.DECEASED

    client.force_authenticate(guard)
    visible = client.get(reverse("death_certificates:death-certificate-list"))
    assert visible.json()["pagination"]["count"] == 1
    printable = client.get(
        reverse(
            "death_certificates:death-certificate-printable",
            kwargs={"pk": certificate_id},
        )
    )
    assert printable.status_code == 200
    assert MedicalRecordAccess.objects.filter(
        user=guard,
        patient=patient,
        action=MedicalRecordAccess.Action.PRINT,
    ).exists()


@pytest.mark.django_db
def test_guard_cannot_create_or_modify_certificate():
    _, _, guard, _, patient = monitoring_context()
    client = APIClient()
    client.force_authenticate(guard)
    response = client.post(
        reverse("death_certificates:death-certificate-list"),
        {
            "patient": str(patient.id),
            "death_datetime": timezone.now().isoformat(),
            "place_of_death": "Unknown",
            "primary_cause": "Unauthorized",
        },
        format="json",
    )
    assert response.status_code == 403
    assert DeathCertificate.objects.count() == 0
