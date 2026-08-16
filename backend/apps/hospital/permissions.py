from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.identity.models import UserRole


class HospitalConfigurationPermission(BasePermission):
    """Head of Service writes; eligible hospital roles may read reference configuration."""

    readable_roles = {
        UserRole.ADMIN,
        UserRole.HEAD_OF_SERVICE,
        UserRole.DOCTOR,
        UserRole.NURSE,
    }

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if request.method in SAFE_METHODS:
            return user.role in self.readable_roles
        return user.role == UserRole.HEAD_OF_SERVICE


class HeadOfServiceOnly(BasePermission):
    message = "Only the Head of Service may perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == UserRole.HEAD_OF_SERVICE
        )
