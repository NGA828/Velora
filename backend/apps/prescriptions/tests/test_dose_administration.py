from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.identity.models import UserRole
from apps.identity.tests.factories import create_staff
from apps.notifications.models import Notification
from apps.prescriptions.models import MedicationDose, MedicationDoseEvent
from apps.prescriptions.services import process_due_dose_notifications
from apps.prescriptions.tests.test_prescription_workflow import (
    prescription_context,
    prescription_payload,
)


def active_dose():
    doctor, nurse, _, patient, medication = prescription_context()
    client = APIClient()
    client.force_authenticate(doctor)
    created = client.post(
        reverse("prescriptions:prescription-list"),
        prescription_payload(patient, medication, days=1),
        format="json",
    )
    client.post(reverse("prescriptions:prescription-activate", kwargs={"pk": created.json()["id"]}))
    dose = MedicationDose.objects.get()
    dose.scheduled_for = timezone.now() - timedelta(minutes=5)
    dose.save(update_fields=["scheduled_for", "updated_at"])
    return doctor, nurse, patient, dose


@pytest.mark.django_db
def test_assigned_nurse_administers_once_and_event_is_append_only():
    _, nurse, _, dose = active_dose()
    client = APIClient()
    client.force_authenticate(nurse)

    administered = client.post(
        reverse("prescriptions:medication-dose-administer", kwargs={"pk": dose.id}),
        {"notes": "Administered after identity check."},
        format="json",
    )
    assert administered.status_code == 200
    assert administered.json()["status"] == MedicationDose.Status.ADMINISTERED
    assert administered.json()["actual_at"] is not None
    assert MedicationDoseEvent.objects.filter(
        dose=dose,
        previous_status="PENDING",
        new_status="ADMINISTERED",
        actor=nurse,
    ).exists()

    duplicate = client.post(
        reverse("prescriptions:medication-dose-administer", kwargs={"pk": dose.id}),
        {"notes": "Duplicate"},
        format="json",
    )
    assert duplicate.status_code == 400
    assert MedicationDoseEvent.objects.filter(dose=dose).count() == 1


@pytest.mark.django_db
def test_refused_dose_requires_notes_and_notifies_doctor():
    doctor, nurse, patient, dose = active_dose()
    client = APIClient()
    client.force_authenticate(nurse)

    no_notes = client.post(
        reverse("prescriptions:medication-dose-refuse", kwargs={"pk": dose.id}),
        {"notes": ""},
        format="json",
    )
    assert no_notes.status_code == 400
    refused = client.post(
        reverse("prescriptions:medication-dose-refuse", kwargs={"pk": dose.id}),
        {"notes": "Patient declined after explanation."},
        format="json",
    )
    assert refused.status_code == 200
    assert refused.json()["status"] == MedicationDose.Status.REFUSED
    assert Notification.objects.filter(
        recipient=doctor, patient=patient, category="MEDICATION_EXCEPTION"
    ).exists()


@pytest.mark.django_db
def test_unassigned_nurse_cannot_see_or_action_dose():
    _, _, _, dose = active_dose()
    unrelated, _ = create_staff(
        role=UserRole.NURSE,
        email="unrelated@example.org",
        employee_number="NUR-009",
    )
    client = APIClient()
    client.force_authenticate(unrelated)

    assert (
        client.get(
            reverse("prescriptions:medication-dose-detail", kwargs={"pk": dose.id})
        ).status_code
        == 404
    )
    assert (
        client.post(
            reverse("prescriptions:medication-dose-administer", kwargs={"pk": dose.id}),
            {},
            format="json",
        ).status_code
        == 404
    )


@pytest.mark.django_db
def test_due_worker_generates_one_idempotent_nurse_alert():
    _, nurse, patient, dose = active_dose()

    assert process_due_dose_notifications(now=timezone.now()) == 1
    assert process_due_dose_notifications(now=timezone.now()) == 0
    assert (
        Notification.objects.filter(
            recipient=nurse,
            patient=patient,
            category="MEDICATION_DUE",
            data__dose_id=str(dose.id),
        ).count()
        == 1
    )
    dose.refresh_from_db()
    assert dose.due_notification_sent_at is not None
