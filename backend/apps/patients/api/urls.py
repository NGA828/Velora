from rest_framework.routers import DefaultRouter

from apps.patients.api.views import PatientViewSet

router = DefaultRouter()
router.register("patients", PatientViewSet, basename="patient")

app_name = "patients"
urlpatterns = router.urls
