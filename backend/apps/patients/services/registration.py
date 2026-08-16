import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.clinical_records.models import MedicalFile
from apps.identity.models import EmploymentStatus, StaffProfile, UserRole
from apps.notifications.services import notify
from apps.patients.models import CareEpisode, Patient, PatientCareAssignment


def _identifier(prefix: str) -> str:
    return f"{prefix}-{timezone.localdate():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"


def _validate_clinical_staff(profile: StaffProfile, role: str) -> None:
    if (
        profile.user.role != role
        or not profile.user.is_active
        or profile.employment_status != EmploymentStatus.ACTIVE
    ):
        raise ValidationError(f"Select an active {role.lower()}.")


@transaction.atomic
def register_patient(
    *,
    doctor,
    assigned_nurse: StaffProfile,
    department,
    patient_data: dict,
    episode_type: str,
    admission_reason: str,
    request=None,
) -> Patient:
    try:
        doctor_profile = doctor.staff_profile
    except StaffProfile.DoesNotExist as exc:
        raise ValidationError("The Doctor staff profile is incomplete.") from exc
    _validate_clinical_staff(doctor_profile, UserRole.DOCTOR)
    _validate_clinical_staff(assigned_nurse, UserRole.NURSE)
    if not department.is_active:
        raise ValidationError("Select an active department.")
    if Patient.objects.filter(
        first_name__iexact=patient_data["first_name"].strip(),
        last_name__iexact=patient_data["last_name"].strip(),
        date_of_birth=patient_data["date_of_birth"],
        status__in=[Patient.Status.REGISTERED, Patient.Status.ADMITTED],
    ).exists():
        raise ValidationError(
            "A current patient with the same name and date of birth already exists."
        )

    now = timezone.now()
    patient_status = (
        Patient.Status.ADMITTED
        if episode_type in {CareEpisode.Type.INPATIENT, CareEpisode.Type.EMERGENCY}
        else Patient.Status.REGISTERED
    )
    patient = Patient(
        medical_record_number=_identifier("VLR"),
        registered_by=doctor,
        status=patient_status,
        **patient_data,
    )
    patient.full_clean()
    patient.save()
    medical_file = MedicalFile.objects.create(
        patient=patient,
        file_number=f"MF-{patient.medical_record_number}",
        opened_at=now,
        opened_by=doctor,
    )
    episode = CareEpisode.objects.create(
        patient=patient,
        episode_number=_identifier("EP"),
        episode_type=episode_type,
        department=department,
        admission_reason=admission_reason,
        admitted_at=now,
    )
    PatientCareAssignment.objects.bulk_create(
        [
            PatientCareAssignment(
                patient=patient,
                care_episode=episode,
                staff=doctor_profile,
                assignment_type=PatientCareAssignment.AssignmentType.DOCTOR,
                starts_at=now,
                assigned_by=doctor,
            ),
            PatientCareAssignment(
                patient=patient,
                care_episode=episode,
                staff=assigned_nurse,
                assignment_type=PatientCareAssignment.AssignmentType.NURSE,
                starts_at=now,
                assigned_by=doctor,
            ),
        ]
    )
    notify(
        recipient=assigned_nurse.user,
        actor=doctor,
        patient=patient,
        category="PATIENT_ASSIGNED",
        title="New patient assigned",
        body=f"{patient.get_full_name()} has been assigned to your care.",
        route=f"/nurse/patients/{patient.id}",
        dedupe_key=f"patient-assignment:{patient.id}:{assigned_nurse.id}",
    )
    record_audit_event(
        actor=doctor,
        request=request,
        action="patients.patient.registered",
        object_type="patients.Patient",
        object_id=patient.id,
        after={
            "medical_record_number": patient.medical_record_number,
            "medical_file_id": str(medical_file.id),
            "care_episode_id": str(episode.id),
            "doctor_staff_id": str(doctor_profile.id),
            "nurse_staff_id": str(assigned_nurse.id),
        },
    )
    return patient


@transaction.atomic
def assign_primary_nurse(*, patient: Patient, nurse: StaffProfile, doctor, request=None):
    _validate_clinical_staff(nurse, UserRole.NURSE)
    if not PatientCareAssignment.objects.filter(
        patient=patient,
        staff__user=doctor,
        assignment_type=PatientCareAssignment.AssignmentType.DOCTOR,
        ends_at__isnull=True,
    ).exists():
        raise ValidationError("Only an assigned Doctor can reassign this patient.")
    episode = patient.care_episodes.filter(status=CareEpisode.Status.ACTIVE).first()
    if not episode:
        raise ValidationError("The patient has no active care episode.")
    now = timezone.now()
    PatientCareAssignment.objects.filter(
        patient=patient,
        assignment_type=PatientCareAssignment.AssignmentType.NURSE,
        ends_at__isnull=True,
    ).update(ends_at=now, is_primary=False)
    assignment = PatientCareAssignment.objects.create(
        patient=patient,
        care_episode=episode,
        staff=nurse,
        assignment_type=PatientCareAssignment.AssignmentType.NURSE,
        starts_at=now,
        assigned_by=doctor,
    )
    notify(
        recipient=nurse.user,
        actor=doctor,
        patient=patient,
        category="PATIENT_ASSIGNED",
        title="Patient assigned",
        body=f"{patient.get_full_name()} has been assigned to your care.",
        route=f"/nurse/patients/{patient.id}",
        dedupe_key=f"patient-assignment:{patient.id}:{nurse.id}:{assignment.id}",
    )
    record_audit_event(
        actor=doctor,
        request=request,
        action="patients.care_assignment.nurse_changed",
        object_type="patients.Patient",
        object_id=patient.id,
        after={"nurse_staff_id": str(nurse.id), "assignment_id": str(assignment.id)},
    )
    return assignment
