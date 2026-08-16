from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.identity.models import UserRole
from apps.identity.services import create_invitation, revoke_invitation
from apps.notifications.services import notify
from apps.patients.models import GuardianAccess, Patient, PatientCareAssignment


@transaction.atomic
def invite_patient_guard(
    *,
    patient: Patient,
    nurse,
    email: str,
    relationship: str,
    permissions: dict,
    request=None,
) -> GuardianAccess:
    if not PatientCareAssignment.objects.filter(
        patient=patient,
        staff__user=nurse,
        assignment_type=PatientCareAssignment.AssignmentType.NURSE,
        ends_at__isnull=True,
    ).exists():
        raise ValidationError("Only an assigned Nurse can invite a Patient Guard.")
    if GuardianAccess.objects.filter(
        patient=patient,
        invitation__email__iexact=email,
        status__in=[GuardianAccess.Status.INVITED, GuardianAccess.Status.ACTIVE],
    ).exists():
        raise ValidationError("This Patient Guard already has a pending or active link.")

    invitation, _ = create_invitation(
        inviter=nurse,
        email=email,
        intended_role=UserRole.PATIENT_GUARD,
        context={"patient_id": str(patient.id)},
        request=request,
    )
    access = GuardianAccess.objects.create(
        patient=patient,
        invitation=invitation,
        relationship=relationship,
        granted_by=nurse,
        can_view_medical_file=permissions.get("can_view_medical_file", True),
        can_answer_monitoring=permissions.get("can_answer_monitoring", True),
        can_decide_transfers=permissions.get("can_decide_transfers", True),
        can_view_billing=permissions.get("can_view_billing", False),
    )
    record_audit_event(
        actor=nurse,
        request=request,
        action="patients.guardian_access.invited",
        object_type="patients.GuardianAccess",
        object_id=access.id,
        after={"patient_id": str(patient.id), "email": email, "relationship": relationship},
    )
    return access


@transaction.atomic
def revoke_guardian_access(*, access: GuardianAccess, actor, request=None) -> GuardianAccess:
    locked = (
        GuardianAccess.objects.select_for_update()
        .select_related("invitation", "guardian__user", "patient")
        .get(pk=access.pk)
    )
    if locked.status == GuardianAccess.Status.REVOKED:
        raise ValidationError("This Patient Guard access has already been revoked.")
    if not PatientCareAssignment.objects.filter(
        patient=locked.patient,
        staff__user=actor,
        assignment_type=PatientCareAssignment.AssignmentType.NURSE,
        ends_at__isnull=True,
    ).exists():
        raise ValidationError("Only an assigned Nurse can revoke Patient Guard access.")

    if locked.status == GuardianAccess.Status.INVITED and locked.invitation.is_pending:
        revoke_invitation(invitation=locked.invitation, actor=actor, request=request)
    locked.status = GuardianAccess.Status.REVOKED
    locked.revoked_at = timezone.now()
    locked.save(update_fields=["status", "revoked_at", "updated_at"])
    if locked.guardian:
        notify(
            recipient=locked.guardian.user,
            actor=actor,
            patient=locked.patient,
            category="GUARDIAN_ACCESS_REVOKED",
            title="Patient access changed",
            body=f"Your access to {locked.patient.get_full_name()} has been revoked.",
            severity="WARNING",
            dedupe_key=f"guardian-revoked:{locked.id}",
        )
    record_audit_event(
        actor=actor,
        request=request,
        action="patients.guardian_access.revoked",
        object_type="patients.GuardianAccess",
        object_id=locked.id,
    )
    return locked
