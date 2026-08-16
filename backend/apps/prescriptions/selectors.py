from apps.identity.models import UserRole
from apps.patients.selectors import patients_visible_to
from apps.prescriptions.models import MedicationDose, Prescription


def prescriptions_visible_to(user):
    queryset = Prescription.objects.filter(patient__in=patients_visible_to(user))
    if user.role == UserRole.NURSE:
        queryset = queryset.exclude(status=Prescription.Status.DRAFT)
    elif user.role == UserRole.PATIENT_GUARD:
        queryset = queryset.filter(activated_at__isnull=False)
    return queryset


def doses_visible_to(user):
    queryset = MedicationDose.objects.filter(
        prescription_item__prescription__patient__in=patients_visible_to(user)
    )
    if user.role == UserRole.PATIENT_GUARD:
        queryset = queryset.filter(prescription_item__prescription__activated_at__isnull=False)
    return queryset
