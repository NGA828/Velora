from rest_framework.routers import DefaultRouter

from apps.prescriptions.api.views import (
    MedicationDoseViewSet,
    MedicationViewSet,
    PrescriptionViewSet,
)

router = DefaultRouter()
router.register("medications", MedicationViewSet, basename="medication")
router.register("prescriptions", PrescriptionViewSet, basename="prescription")
router.register("medication-doses", MedicationDoseViewSet, basename="medication-dose")

app_name = "prescriptions"
urlpatterns = router.urls
