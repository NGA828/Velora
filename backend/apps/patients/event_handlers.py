from django.core.exceptions import ValidationError
from django.dispatch import receiver
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.identity.events import invitation_accepted
from apps.identity.models import Invitation, PatientGuardProfile, UserRole
from apps.notifications.services import notify
from apps.patients.models import GuardianAccess, PatientCareAssignment


@receiver(invitation_accepted, sender=Invitation)
def activate_guardian_access(*, invitation, user, request=None, **kwargs) -> None:
    if invitation.intended_role != UserRole.PATIENT_GUARD:
        return
    try:
        access = (
            GuardianAccess.objects.select_for_update()
            .select_related("patient")
            .get(invitation=invitation)
        )
    except GuardianAccess.DoesNotExist:
        return
    try:
        guardian = user.patient_guard_profile
    except PatientGuardProfile.DoesNotExist as exc:
        raise ValidationError("The Patient Guard profile could not be created.") from exc
    if (
        GuardianAccess.objects.filter(
            patient=access.patient,
            guardian=guardian,
            status=GuardianAccess.Status.ACTIVE,
        )
        .exclude(pk=access.pk)
        .exists()
    ):
        raise ValidationError("This Patient Guard already has active access to the patient.")

    access.guardian = guardian
    access.status = GuardianAccess.Status.ACTIVE
    access.granted_at = timezone.now()
    access.save(update_fields=["guardian", "status", "granted_at", "updated_at"])
    doctor_assignments = PatientCareAssignment.objects.filter(
        patient=access.patient,
        assignment_type=PatientCareAssignment.AssignmentType.DOCTOR,
        ends_at__isnull=True,
    ).select_related("staff__user")
    for assignment in doctor_assignments:
        notify(
            recipient=assignment.staff.user,
            actor=user,
            patient=access.patient,
            category="GUARDIAN_ACCESS_ACTIVE",
            title="Patient Guard access activated",
            body=(
                f"{user.get_full_name()} now has authorized access to "
                f"{access.patient.get_full_name()}."
            ),
            route=f"/doctor/patients/{access.patient.id}",
            dedupe_key=f"guardian-active:{access.id}:{assignment.staff.user_id}",
        )
    record_audit_event(
        actor=user,
        request=request,
        action="patients.guardian_access.activated",
        object_type="patients.GuardianAccess",
        object_id=access.id,
        after={"patient_id": str(access.patient_id), "guardian_user_id": str(user.id)},
    )
