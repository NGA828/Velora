from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.patients.models import PatientCareAssignment
from apps.prescriptions.models import MedicationDose, MedicationDoseEvent

NURSE_OUTCOMES = {
    MedicationDose.Status.ADMINISTERED,
    MedicationDose.Status.MISSED,
    MedicationDose.Status.REFUSED,
}


@transaction.atomic
def record_dose_outcome(
    *, dose: MedicationDose, nurse, outcome: str, notes: str = "", request=None
) -> MedicationDose:
    locked = (
        MedicationDose.objects.select_for_update()
        .select_related("prescription_item__prescription__patient")
        .get(pk=dose.pk)
    )
    patient = locked.prescription_item.prescription.patient
    if outcome not in NURSE_OUTCOMES:
        raise ValidationError("Select a valid medication outcome.")
    if not PatientCareAssignment.objects.filter(
        patient=patient,
        staff__user=nurse,
        assignment_type=PatientCareAssignment.AssignmentType.NURSE,
        ends_at__isnull=True,
    ).exists():
        raise ValidationError("Only an assigned Nurse can record this medication outcome.")
    if locked.status != MedicationDose.Status.PENDING:
        raise ValidationError("This medication dose has already been resolved.")
    if (
        outcome in {MedicationDose.Status.MISSED, MedicationDose.Status.REFUSED}
        and not notes.strip()
    ):
        raise ValidationError("Notes are required for a missed or refused dose.")

    now = timezone.now()
    previous = locked.status
    locked.status = outcome
    locked.actual_at = now
    locked.acted_by = nurse
    locked.notes = notes
    locked.save(update_fields=["status", "actual_at", "acted_by", "notes", "updated_at"])
    MedicationDoseEvent.objects.create(
        dose=locked,
        actor=nurse,
        previous_status=previous,
        new_status=outcome,
        occurred_at=now,
        notes=notes,
    )
    if outcome in {MedicationDose.Status.MISSED, MedicationDose.Status.REFUSED}:
        doctor_assignments = PatientCareAssignment.objects.filter(
            patient=patient,
            assignment_type=PatientCareAssignment.AssignmentType.DOCTOR,
            ends_at__isnull=True,
        ).select_related("staff__user")
        medication = locked.prescription_item.medication
        for assignment in doctor_assignments:
            notify(
                recipient=assignment.staff.user,
                actor=nurse,
                patient=patient,
                category="MEDICATION_EXCEPTION",
                severity=Notification.Severity.WARNING,
                title=f"Medication {outcome.lower()}",
                body=(
                    f"{medication.generic_name} was marked {outcome.lower()} for "
                    f"{patient.get_full_name()}."
                ),
                route=f"/doctor/patients/{patient.id}/prescriptions",
                data={"dose_id": str(locked.id)},
                dedupe_key=f"medication-exception:{locked.id}:{assignment.staff.user_id}",
            )
    record_audit_event(
        actor=nurse,
        request=request,
        action="prescriptions.medication_dose.outcome_recorded",
        object_type="prescriptions.MedicationDose",
        object_id=locked.id,
        after={
            "patient_id": str(patient.id),
            "status": outcome,
            "scheduled_for": locked.scheduled_for.isoformat(),
            "actual_at": now.isoformat(),
        },
    )
    return locked


@transaction.atomic
def process_due_dose_notifications(*, now=None) -> int:
    now = now or timezone.now()
    due_doses = list(
        MedicationDose.objects.select_for_update(skip_locked=True)
        .filter(
            status=MedicationDose.Status.PENDING,
            scheduled_for__lte=now,
            due_notification_sent_at__isnull=True,
            prescription_item__prescription__status="ACTIVE",
        )
        .select_related(
            "prescription_item__medication",
            "prescription_item__prescription__patient",
        )[:500]
    )
    sent = 0
    for dose in due_doses:
        patient = dose.prescription_item.prescription.patient
        assignments = PatientCareAssignment.objects.filter(
            patient=patient,
            assignment_type=PatientCareAssignment.AssignmentType.NURSE,
            ends_at__isnull=True,
            staff__user__is_active=True,
        ).select_related("staff__user")
        delivered = False
        for assignment in assignments:
            notify(
                recipient=assignment.staff.user,
                patient=patient,
                category="MEDICATION_DUE",
                severity=Notification.Severity.WARNING,
                title="Medication dose due",
                body=(
                    f"{dose.prescription_item.medication.generic_name} is due for "
                    f"{patient.get_full_name()}."
                ),
                route="/nurse/medication",
                data={"dose_id": str(dose.id)},
                dedupe_key=f"medication-due:{dose.id}:{assignment.staff.user_id}",
            )
            delivered = True
        if delivered:
            dose.due_notification_sent_at = now
            dose.save(update_fields=["due_notification_sent_at", "updated_at"])
            sent += 1
    return sent
