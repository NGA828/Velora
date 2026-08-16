import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.prescriptions.models import MedicationDose, MedicationDoseEvent, Prescription
from apps.prescriptions.tests.test_prescription_workflow import (
    prescription_context,
    prescription_payload,
)


@pytest.mark.django_db
def test_cancelling_active_prescription_cancels_all_pending_doses():
    doctor, _, _, patient, medication = prescription_context()
    client = APIClient()
    client.force_authenticate(doctor)
    created = client.post(
        reverse("prescriptions:prescription-list"),
        prescription_payload(patient, medication, days=2),
        format="json",
    )
    client.post(reverse("prescriptions:prescription-activate", kwargs={"pk": created.json()["id"]}))

    cancelled = client.post(
        reverse("prescriptions:prescription-cancel", kwargs={"pk": created.json()["id"]}),
        {"reason": "Treatment plan changed."},
        format="json",
    )

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == Prescription.Status.CANCELLED
    assert MedicationDose.objects.filter(status=MedicationDose.Status.CANCELLED).count() == 2
    assert MedicationDoseEvent.objects.filter(new_status="CANCELLED").count() == 2
