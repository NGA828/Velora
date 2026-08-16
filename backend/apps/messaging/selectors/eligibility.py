from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.identity.models import UserRole
from apps.patients.models import GuardianAccess, PatientCareAssignment

User = get_user_model()


def eligible_users_for(user):
    queryset = User.objects.filter(is_active=True).exclude(pk=user.pk)
    if user.role == UserRole.HEAD_OF_SERVICE:
        return queryset.filter(role__in=[UserRole.DOCTOR, UserRole.NURSE])
    if user.role in {UserRole.ADMIN, UserRole.ACCOUNTING}:
        return queryset.filter(role=UserRole.HEAD_OF_SERVICE)
    if user.role in {UserRole.DOCTOR, UserRole.NURSE}:
        patient_ids = PatientCareAssignment.objects.filter(
            staff__user=user,
            ends_at__isnull=True,
        ).values_list("patient_id", flat=True)
        clinical_ids = PatientCareAssignment.objects.filter(
            patient_id__in=patient_ids,
            ends_at__isnull=True,
        ).values_list("staff__user_id", flat=True)
        guardian_ids = GuardianAccess.objects.filter(
            patient_id__in=patient_ids,
            status=GuardianAccess.Status.ACTIVE,
        ).values_list("guardian__user_id", flat=True)
        return queryset.filter(
            Q(id__in=clinical_ids) | Q(id__in=guardian_ids) | Q(role=UserRole.HEAD_OF_SERVICE)
        ).distinct()
    if user.role == UserRole.PATIENT_GUARD:
        patient_ids = GuardianAccess.objects.filter(
            guardian__user=user,
            status=GuardianAccess.Status.ACTIVE,
        ).values_list("patient_id", flat=True)
        staff_ids = PatientCareAssignment.objects.filter(
            patient_id__in=patient_ids,
            ends_at__isnull=True,
        ).values_list("staff__user_id", flat=True)
        return queryset.filter(id__in=staff_ids).distinct()
    return queryset.none()


def user_can_access_patient(user, patient) -> bool:
    if user.role in {UserRole.DOCTOR, UserRole.NURSE}:
        return PatientCareAssignment.objects.filter(
            patient=patient,
            staff__user=user,
            ends_at__isnull=True,
        ).exists()
    if user.role == UserRole.PATIENT_GUARD:
        return GuardianAccess.objects.filter(
            patient=patient,
            guardian__user=user,
            status=GuardianAccess.Status.ACTIVE,
        ).exists()
    return False


def users_may_communicate(*, first, second, patient=None) -> bool:
    if not eligible_users_for(first).filter(pk=second.pk).exists():
        return False
    if patient and not (
        user_can_access_patient(first, patient) and user_can_access_patient(second, patient)
    ):
        return False
    return True
