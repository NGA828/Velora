from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.identity.events import invitation_accepted
from apps.identity.models import (
    Invitation,
    PatientGuardProfile,
    StaffProfile,
    User,
    UserRole,
)
from integrations.email.invitations import send_invitation_email

logger = logging.getLogger(__name__)

STAFF_ROLES = {
    UserRole.ADMIN,
    UserRole.HEAD_OF_SERVICE,
    UserRole.DOCTOR,
    UserRole.NURSE,
    UserRole.ACCOUNTING,
}


def _token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def allowed_invitation_roles(inviter: User) -> set[str]:
    if inviter.role == UserRole.ADMIN:
        return {
            UserRole.ADMIN,
            UserRole.HEAD_OF_SERVICE,
            UserRole.DOCTOR,
            UserRole.NURSE,
            UserRole.ACCOUNTING,
        }
    if inviter.role == UserRole.HEAD_OF_SERVICE:
        return {UserRole.DOCTOR, UserRole.NURSE}
    if inviter.role == UserRole.NURSE:
        return {UserRole.PATIENT_GUARD}
    return set()


@transaction.atomic
def create_invitation(
    *,
    inviter: User,
    email: str,
    intended_role: str,
    context: dict | None = None,
    request=None,
    expires_in: timedelta = timedelta(hours=72),
) -> tuple[Invitation, str]:
    email = User.objects.normalize_email(email).lower()
    if intended_role not in allowed_invitation_roles(inviter):
        raise ValidationError("You cannot invite a user with this role.")
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError("An account already exists for this email address.")
    if Invitation.objects.filter(
        email__iexact=email,
        intended_role=intended_role,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).exists():
        raise ValidationError("A pending invitation already exists for this email and role.")

    profile_context = context or {}
    employee_number = profile_context.get("employee_number")
    if intended_role in STAFF_ROLES and not employee_number:
        raise ValidationError("An employee number is required for a staff invitation.")
    if employee_number and (
        StaffProfile.objects.filter(employee_number__iexact=employee_number).exists()
        or Invitation.objects.filter(
            context__employee_number=employee_number,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).exists()
    ):
        raise ValidationError("This employee number is already in use or reserved.")

    raw_token = secrets.token_urlsafe(32)
    invitation = Invitation.objects.create(
        email=email,
        intended_role=intended_role,
        token_hash=_token_hash(raw_token),
        expires_at=timezone.now() + expires_in,
        invited_by=inviter,
        context=profile_context,
    )
    record_audit_event(
        actor=inviter,
        request=request,
        action="identity.invitation.created",
        object_type="identity.Invitation",
        object_id=invitation.id,
        after={"email": email, "role": intended_role},
    )

    def deliver_invitation() -> None:
        try:
            send_invitation_email(invitation=invitation, raw_token=raw_token)
        except Exception:
            logger.exception("Invitation email delivery failed for invitation %s", invitation.id)

    transaction.on_commit(deliver_invitation)
    return invitation, raw_token


@transaction.atomic
def accept_invitation(
    *,
    raw_token: str,
    first_name: str,
    last_name: str,
    phone: str,
    password: str,
    request=None,
) -> User:
    token_hash = _token_hash(raw_token)
    try:
        invitation = Invitation.objects.select_for_update().get(token_hash=token_hash)
    except Invitation.DoesNotExist as exc:
        raise ValidationError("This invitation is invalid or no longer available.") from exc

    if invitation.revoked_at or invitation.accepted_at or invitation.is_expired:
        raise ValidationError("This invitation is invalid or no longer available.")
    if User.objects.filter(email__iexact=invitation.email).exists():
        raise ValidationError("An account already exists for this invitation.")

    pending_user = User(
        email=invitation.email,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        phone=phone.strip(),
        role=invitation.intended_role,
    )
    validate_password(password, user=pending_user)
    pending_user.set_password(password)
    pending_user.must_change_password = False
    pending_user.save()

    context = invitation.context
    if invitation.intended_role in STAFF_ROLES:
        StaffProfile.objects.create(
            user=pending_user,
            employee_number=context["employee_number"],
            department_id=context.get("department_id") or None,
            job_title=context.get("job_title", ""),
            license_number=context.get("license_number", ""),
            hire_date=context.get("hire_date") or None,
        )
    elif invitation.intended_role == UserRole.PATIENT_GUARD:
        PatientGuardProfile.objects.create(user=pending_user)

    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at", "updated_at"])
    invitation_accepted.send(
        sender=Invitation,
        invitation=invitation,
        user=pending_user,
        request=request,
    )
    record_audit_event(
        actor=pending_user,
        request=request,
        action="identity.invitation.accepted",
        object_type="identity.Invitation",
        object_id=invitation.id,
        after={"user_id": str(pending_user.id), "role": pending_user.role},
    )
    return pending_user


@transaction.atomic
def revoke_invitation(*, invitation: Invitation, actor: User, request=None) -> Invitation:
    locked = Invitation.objects.select_for_update().get(pk=invitation.pk)
    if not locked.is_pending:
        raise ValidationError("Only a pending invitation can be revoked.")
    locked.revoked_at = timezone.now()
    locked.save(update_fields=["revoked_at", "updated_at"])
    record_audit_event(
        actor=actor,
        request=request,
        action="identity.invitation.revoked",
        object_type="identity.Invitation",
        object_id=locked.id,
    )
    return locked
