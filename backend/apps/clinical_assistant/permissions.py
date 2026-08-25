from rest_framework.permissions import BasePermission

from apps.identity.models import UserRole
from apps.patients.models import GuardianAccess, Patient, PatientCareAssignment
from apps.patients.selectors import patients_visible_to


class ClinicalAssistantPermission(BasePermission):
    """
    Permission check ensuring the user has active, authorized access
    to the specific patient before interacting with the Clinical Assistant.
    """

    allowed_roles = {
        UserRole.DOCTOR,
        UserRole.NURSE,
        UserRole.PATIENT_GUARD,
        UserRole.HEAD_OF_SERVICE,
    }

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        return user.role in self.allowed_roles

    @staticmethod
    def user_can_access_patient(*, user, patient: Patient) -> bool:
        if not user or not user.is_authenticated or not user.is_active:
            return False

        if user.role == UserRole.HEAD_OF_SERVICE:
            return True

        if user.role in {UserRole.DOCTOR, UserRole.NURSE}:
            return PatientCareAssignment.objects.filter(
                patient=patient,
                staff__user=user,
                assignment_type=user.role,
                ends_at__isnull=True,
            ).exists()

        if user.role == UserRole.PATIENT_GUARD:
            return GuardianAccess.objects.filter(
                patient=patient,
                guardian__user=user,
                status=GuardianAccess.Status.ACTIVE,
            ).exists()

        return False
