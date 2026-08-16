from .files import MedicalFileViewSet
from .records import (
    AllergyViewSet,
    ClinicalNoteViewSet,
    DiagnosisViewSet,
    MedicalHistoryEntryViewSet,
    TreatmentPlanViewSet,
)

__all__ = [
    "AllergyViewSet",
    "ClinicalNoteViewSet",
    "DiagnosisViewSet",
    "MedicalFileViewSet",
    "MedicalHistoryEntryViewSet",
    "TreatmentPlanViewSet",
]
