from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.identity.models import UserRole


class TransferPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if request.method in SAFE_METHODS:
            return user.role in {UserRole.DOCTOR, UserRole.PATIENT_GUARD}
        action = getattr(view, "action", None)
        if action in {"create", "recommend", "submit", "send_package"}:
            return user.role == UserRole.DOCTOR
        if action == "decide":
            return user.role == UserRole.PATIENT_GUARD
        return False
