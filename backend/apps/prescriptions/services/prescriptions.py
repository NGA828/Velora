from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.hospital.models import HospitalProfile
from apps.notifications.services import notify
from apps.patients.models import GuardianAccess, Patient, PatientCareAssignment
from apps.prescriptions.models import (
    DoseScheduleRule,
    MedicationDose,
    MedicationDoseEvent,
    Prescription,
    PrescriptionItem,
)

MAX_PRESCRIPTION_DAYS = 366


def _assigned_doctor(*, patient: Patient, doctor) -> bool:
    return PatientCareAssignment.objects.filter(
        patient=patient,
        staff__user=doctor,
        assignment_type=PatientCareAssignment.AssignmentType.DOCTOR,
        ends_at__isnull=True,
    ).exists()


def _hospital_timezone() -> str:
    profile = HospitalProfile.objects.first()
    return profile.timezone if profile else settings.TIME_ZONE


@transaction.atomic
def create_prescription(
    *,
    doctor,
    patient: Patient,
    starts_on,
    ends_on,
    clinical_instructions: str,
    items: list[dict],
    request=None,
) -> Prescription:
    if not _assigned_doctor(patient=patient, doctor=doctor):
        raise ValidationError("Only an assigned Doctor can prescribe for this patient.")
    episode = patient.care_episodes.filter(status="ACTIVE").first()
    if not episode:
        raise ValidationError("The patient has no active care episode.")
    duration = (ends_on - starts_on).days + 1
    if duration < 1 or duration > MAX_PRESCRIPTION_DAYS:
        raise ValidationError(
            f"Prescription duration must be between 1 and {MAX_PRESCRIPTION_DAYS} days."
        )
    if not items:
        raise ValidationError("Add at least one medication item.")

    timezone_name = _hospital_timezone()
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValidationError("The hospital timezone is not valid.") from exc

    prescription = Prescription.objects.create(
        patient=patient,
        care_episode=episode,
        prescribed_by=doctor,
        prescribed_at=timezone.now(),
        starts_on=starts_on,
        ends_on=ends_on,
        clinical_instructions=clinical_instructions,
    )
    for item_data in items:
        schedules = item_data.pop("schedules")
        if item_data["schedule_type"] == PrescriptionItem.ScheduleType.SCHEDULED:
            if not schedules:
                raise ValidationError("Every scheduled medication requires at least one dose time.")
            if any(
                day not in range(7)
                for schedule in schedules
                for day in schedule.get("days_of_week", [])
            ):
                raise ValidationError("Days of week must use values from 0 (Monday) to 6 (Sunday).")
        item = PrescriptionItem.objects.create(
            prescription=prescription,
            **item_data,
        )
        for schedule in schedules:
            DoseScheduleRule.objects.create(
                prescription_item=item,
                local_time=schedule["local_time"],
                days_of_week=schedule.get("days_of_week", []),
                timezone=timezone_name,
            )
    record_audit_event(
        actor=doctor,
        request=request,
        action="prescriptions.prescription.created",
        object_type="prescriptions.Prescription",
        object_id=prescription.id,
        after={
            "patient_id": str(patient.id),
            "starts_on": starts_on.isoformat(),
            "ends_on": ends_on.isoformat(),
            "item_count": len(items),
        },
    )
    return prescription


@transaction.atomic
def activate_prescription(*, prescription: Prescription, doctor, request=None) -> Prescription:
    locked = (
        Prescription.objects.select_for_update().select_related("patient").get(pk=prescription.pk)
    )
    if not _assigned_doctor(patient=locked.patient, doctor=doctor):
        raise ValidationError("Only an assigned Doctor can activate this prescription.")
    if locked.status != Prescription.Status.DRAFT:
        raise ValidationError("Only a draft prescription can be activated.")
    items = list(locked.items.select_related("medication").prefetch_related("schedule_rules"))
    if not items:
        raise ValidationError("A prescription must contain at least one medication item.")

    generated: list[MedicationDose] = []
    for item in items:
        if item.schedule_type != PrescriptionItem.ScheduleType.SCHEDULED:
            continue
        rules = list(item.schedule_rules.all())
        if not rules:
            raise ValidationError(f"{item.medication} has no schedule times.")
        item_end = min(locked.ends_on, locked.starts_on + timedelta(days=item.duration_days - 1))
        day = locked.starts_on
        while day <= item_end:
            for rule in rules:
                if rule.days_of_week and day.weekday() not in rule.days_of_week:
                    continue
                scheduled_local = datetime.combine(
                    day,
                    rule.local_time,
                    tzinfo=ZoneInfo(rule.timezone),
                )
                generated.append(
                    MedicationDose(
                        prescription_item=item,
                        scheduled_for=scheduled_local.astimezone(ZoneInfo("UTC")),
                    )
                )
            day += timedelta(days=1)
    if not generated and any(
        item.schedule_type == PrescriptionItem.ScheduleType.SCHEDULED for item in items
    ):
        raise ValidationError("The configured schedule did not generate any medication doses.")
    MedicationDose.objects.bulk_create(generated)
    locked.status = Prescription.Status.ACTIVE
    locked.activated_at = timezone.now()
    locked.save(update_fields=["status", "activated_at", "updated_at"])
    _notify_prescription_active(locked, doctor)
    record_audit_event(
        actor=doctor,
        request=request,
        action="prescriptions.prescription.activated",
        object_type="prescriptions.Prescription",
        object_id=locked.id,
        after={"dose_count": len(generated), "activated_at": locked.activated_at.isoformat()},
    )
    return locked


def _notify_prescription_active(prescription: Prescription, actor) -> None:
    patient = prescription.patient
    nurse_assignments = PatientCareAssignment.objects.filter(
        patient=patient,
        assignment_type=PatientCareAssignment.AssignmentType.NURSE,
        ends_at__isnull=True,
    ).select_related("staff__user")
    for assignment in nurse_assignments:
        notify(
            recipient=assignment.staff.user,
            actor=actor,
            patient=patient,
            category="PRESCRIPTION_ACTIVE",
            title="New active prescription",
            body=(
                f"A prescription for {patient.get_full_name()} is ready for medication scheduling."
            ),
            route="/nurse/medication",
            dedupe_key=f"prescription-active:{prescription.id}:{assignment.staff.user_id}",
        )
    guard_accesses = GuardianAccess.objects.filter(
        patient=patient,
        status=GuardianAccess.Status.ACTIVE,
    ).select_related("guardian__user")
    for access in guard_accesses:
        notify(
            recipient=access.guardian.user,
            actor=actor,
            patient=patient,
            category="PRESCRIPTION_AVAILABLE",
            title="New prescription available",
            body=f"A new prescription for {patient.get_full_name()} is available to view.",
            route="/patient-guard/prescriptions",
            dedupe_key=f"prescription-guard:{prescription.id}:{access.guardian.user_id}",
        )


@transaction.atomic
def cancel_prescription(
    *, prescription: Prescription, doctor, reason: str, request=None
) -> Prescription:
    locked = (
        Prescription.objects.select_for_update().select_related("patient").get(pk=prescription.pk)
    )
    if not _assigned_doctor(patient=locked.patient, doctor=doctor):
        raise ValidationError("Only an assigned Doctor can cancel this prescription.")
    if locked.status not in {Prescription.Status.DRAFT, Prescription.Status.ACTIVE}:
        raise ValidationError("This prescription cannot be cancelled from its current state.")
    if not reason.strip():
        raise ValidationError("A cancellation reason is required.")
    now = timezone.now()
    pending_doses = list(
        MedicationDose.objects.select_for_update().filter(
            prescription_item__prescription=locked,
            status=MedicationDose.Status.PENDING,
        )
    )
    for dose in pending_doses:
        dose.status = MedicationDose.Status.CANCELLED
        dose.acted_by = doctor
        dose.actual_at = now
        dose.notes = reason
    MedicationDose.objects.bulk_update(
        pending_doses,
        ["status", "acted_by", "actual_at", "notes", "updated_at"],
    )
    MedicationDoseEvent.objects.bulk_create(
        [
            MedicationDoseEvent(
                dose=dose,
                actor=doctor,
                previous_status=MedicationDose.Status.PENDING,
                new_status=MedicationDose.Status.CANCELLED,
                occurred_at=now,
                notes=reason,
            )
            for dose in pending_doses
        ]
    )
    locked.status = Prescription.Status.CANCELLED
    locked.cancelled_at = now
    locked.cancellation_reason = reason
    locked.save(
        update_fields=[
            "status",
            "cancelled_at",
            "cancellation_reason",
            "updated_at",
        ]
    )
    record_audit_event(
        actor=doctor,
        request=request,
        action="prescriptions.prescription.cancelled",
        object_type="prescriptions.Prescription",
        object_id=locked.id,
        reason=reason,
        after={"cancelled_dose_count": len(pending_doses)},
    )
    return locked


@transaction.atomic
def complete_prescription(*, prescription: Prescription, doctor, request=None) -> Prescription:
    locked = (
        Prescription.objects.select_for_update().select_related("patient").get(pk=prescription.pk)
    )
    if not _assigned_doctor(patient=locked.patient, doctor=doctor):
        raise ValidationError("Only an assigned Doctor can complete this prescription.")
    if locked.status != Prescription.Status.ACTIVE:
        raise ValidationError("Only an active prescription can be completed.")
    if MedicationDose.objects.filter(
        prescription_item__prescription=locked,
        status=MedicationDose.Status.PENDING,
    ).exists():
        raise ValidationError("Resolve all pending medication doses before completion.")
    locked.status = Prescription.Status.COMPLETED
    locked.completed_at = timezone.now()
    locked.save(update_fields=["status", "completed_at", "updated_at"])
    record_audit_event(
        actor=doctor,
        request=request,
        action="prescriptions.prescription.completed",
        object_type="prescriptions.Prescription",
        object_id=locked.id,
    )
    return locked
