from rest_framework.permissions import BasePermission

from apps.identity.models import UserRole


class CanViewClinicalStaffDirectory(BasePermission):
    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role in {UserRole.HEAD_OF_SERVICE, UserRole.DOCTOR, UserRole.NURSE}
        )


class CanManageStaff(BasePermission):
    message = "Only an Admin or Head of Service may manage staff."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role in {UserRole.ADMIN, UserRole.HEAD_OF_SERVICE}
        )
