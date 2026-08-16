from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.identity.models import UserRole


class MonitoringPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if request.method in SAFE_METHODS:
            return user.role in {UserRole.DOCTOR, UserRole.PATIENT_GUARD}
        action = getattr(view, "action", None)
        if action in {"create", "add_question", "close"}:
            return user.role == UserRole.DOCTOR
        if action == "answer":
            return user.role == UserRole.PATIENT_GUARD
        return False
