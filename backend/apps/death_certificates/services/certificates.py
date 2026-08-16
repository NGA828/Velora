import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.death_certificates.models import DeathCertificate
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.patients.models import GuardianAccess, Patient, PatientCareAssignment


def _doctor_assigned(patient, doctor) -> bool:
    return PatientCareAssignment.objects.filter(
        patient=patient,
        staff__user=doctor,
        assignment_type=PatientCareAssignment.AssignmentType.DOCTOR,
        ends_at__isnull=True,
    ).exists()


def _certificate_number():
    return f"DC-{timezone.localdate():%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"


@transaction.atomic
def create_certificate(*, patient, doctor, data, request=None):
    if not _doctor_assigned(patient, doctor):
        raise ValidationError("Only an assigned Doctor can create this certificate.")
    if data["death_datetime"] > timezone.now():
        raise ValidationError("Death date and time cannot be in the future.")
    if patient.death_certificates.filter(status=DeathCertificate.Status.ISSUED).exists():
        raise ValidationError("An issued death certificate already exists for this patient.")
    certificate = DeathCertificate.objects.create(
        certificate_number=_certificate_number(),
        patient=patient,
        issuing_doctor=doctor,
        **data,
    )
    record_audit_event(
        actor=doctor,
        request=request,
        action="death_certificates.certificate.created",
        object_type="death_certificates.DeathCertificate",
        object_id=certificate.id,
        after={"patient_id": str(patient.id), "status": certificate.status},
    )
    return certificate


@transaction.atomic
def issue_certificate(*, certificate, doctor, request=None):
    locked = (
        DeathCertificate.objects.select_for_update()
        .select_related("patient")
        .get(pk=certificate.pk)
    )
    if locked.issuing_doctor_id != doctor.id or not _doctor_assigned(locked.patient, doctor):
        raise ValidationError("Only the issuing assigned Doctor can issue this certificate.")
    if locked.status != DeathCertificate.Status.DRAFT:
        raise ValidationError("Only a draft certificate can be issued.")
    if (
        DeathCertificate.objects.filter(
            patient=locked.patient, status=DeathCertificate.Status.ISSUED
        )
        .exclude(pk=locked.pk)
        .exists()
    ):
        raise ValidationError("An issued death certificate already exists for this patient.")
    now = timezone.now()
    locked.status = DeathCertificate.Status.ISSUED
    locked.issued_at = now
    locked.save(update_fields=["status", "issued_at", "updated_at"])
    patient = locked.patient
    patient.status = Patient.Status.DECEASED
    patient.save(update_fields=["status", "updated_at"])
    accesses = GuardianAccess.objects.filter(
        patient=patient, status=GuardianAccess.Status.ACTIVE
    ).select_related("guardian__user")
    for access in accesses:
        notify(
            recipient=access.guardian.user,
            actor=doctor,
            patient=patient,
            category="DEATH_CERTIFICATE_ISSUED",
            severity=Notification.Severity.INFORMATION,
            title="Death certificate available",
            body=(
                f"An issued certificate for {patient.get_full_name()} is available "
                "to view and print."
            ),
            route="/patient-guard/death-certificates",
            dedupe_key=f"death-certificate:{locked.id}:{access.guardian.user_id}",
        )
    record_audit_event(
        actor=doctor,
        request=request,
        action="death_certificates.certificate.issued",
        object_type="death_certificates.DeathCertificate",
        object_id=locked.id,
        after={"issued_at": now.isoformat(), "certificate_number": locked.certificate_number},
    )
    return locked


@transaction.atomic
def void_certificate(*, certificate, doctor, reason, request=None):
    locked = DeathCertificate.objects.select_for_update().get(pk=certificate.pk)
    if locked.issuing_doctor_id != doctor.id:
        raise ValidationError("Only the issuing Doctor can void this certificate.")
    if locked.status != DeathCertificate.Status.ISSUED:
        raise ValidationError("Only an issued certificate can be voided.")
    if not reason.strip():
        raise ValidationError("A void reason is required.")
    now = timezone.now()
    locked.status = DeathCertificate.Status.VOID
    locked.voided_at = now
    locked.voided_by = doctor
    locked.void_reason = reason
    locked.save(
        update_fields=[
            "status",
            "voided_at",
            "voided_by",
            "void_reason",
            "updated_at",
        ]
    )
    record_audit_event(
        actor=doctor,
        request=request,
        action="death_certificates.certificate.voided",
        object_type="death_certificates.DeathCertificate",
        object_id=locked.id,
        reason=reason,
    )
    return locked
