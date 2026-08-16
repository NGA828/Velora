from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.identity.models import UserRole


class MedicationCatalogPermission(BasePermission):
    readable_roles = {UserRole.HEAD_OF_SERVICE, UserRole.DOCTOR, UserRole.NURSE}

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if request.method in SAFE_METHODS:
            return user.role in self.readable_roles
        return user.role == UserRole.HEAD_OF_SERVICE


class PrescriptionPermission(BasePermission):
    readable_roles = {UserRole.DOCTOR, UserRole.NURSE, UserRole.PATIENT_GUARD}

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if request.method in SAFE_METHODS:
            return user.role in self.readable_roles
        action = getattr(view, "action", None)
        if action in {"create", "activate", "cancel", "complete"}:
            return user.role == UserRole.DOCTOR
        if action in {"administer", "miss", "refuse"}:
            return user.role == UserRole.NURSE
        return False
