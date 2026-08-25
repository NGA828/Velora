from rest_framework.routers import DefaultRouter

from apps.clinical_records.api.views import (
    AllergyViewSet,
    ClinicalNoteViewSet,
    DiagnosisViewSet,
    MedicalFileAttachmentViewSet,
    MedicalFileViewSet,
    MedicalHistoryEntryViewSet,
    TreatmentPlanViewSet,
)

router = DefaultRouter()
router.register("medical-files", MedicalFileViewSet, basename="medical-file")
router.register(
    "medical-file-attachments", MedicalFileAttachmentViewSet, basename="medical-file-attachment"
)
router.register("allergies", AllergyViewSet, basename="allergy")
router.register("medical-history", MedicalHistoryEntryViewSet, basename="medical-history")
router.register("diagnoses", DiagnosisViewSet, basename="diagnosis")
router.register("treatment-plans", TreatmentPlanViewSet, basename="treatment-plan")
router.register("clinical-notes", ClinicalNoteViewSet, basename="clinical-note")

app_name = "clinical_records"
urlpatterns = router.urls
