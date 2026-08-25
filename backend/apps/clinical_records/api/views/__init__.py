from .attachments import MedicalFileAttachmentViewSet
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
    "MedicalFileAttachmentViewSet",
    "MedicalFileViewSet",
    "MedicalHistoryEntryViewSet",
    "TreatmentPlanViewSet",
]
