from rest_framework.permissions import BasePermission

from apps.identity.models import UserRole


class PatientAccessPermission(BasePermission):
    readable_roles = {UserRole.DOCTOR, UserRole.NURSE, UserRole.PATIENT_GUARD}

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        action = getattr(view, "action", None)
        if action in {"create", "partial_update", "update", "assign_nurse"}:
            return user.role == UserRole.DOCTOR
        if action in {"guardians", "revoke_guardian"}:
            return user.role in {UserRole.DOCTOR, UserRole.NURSE}
        if action == "destroy":
            return False
        return user.role in self.readable_roles
