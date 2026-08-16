from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.hospital.api.views import (
    BedViewSet,
    ClinicalConditionViewSet,
    DepartmentViewSet,
    ExternalHospitalServiceViewSet,
    ExternalHospitalSpecialtyViewSet,
    ExternalHospitalViewSet,
    ExternalSpecialistViewSet,
    HeadOfServiceDashboardView,
    HospitalProfileView,
    HospitalServiceAvailabilityViewSet,
    ResourceViewSet,
    RoomViewSet,
    ServiceDefinitionViewSet,
    SpecialtyConditionViewSet,
    SpecialtyViewSet,
)

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("specialties", SpecialtyViewSet, basename="specialty")
router.register("clinical-conditions", ClinicalConditionViewSet, basename="clinical-condition")
router.register(
    "specialty-condition-mappings",
    SpecialtyConditionViewSet,
    basename="specialty-condition-mapping",
)
router.register("services", ServiceDefinitionViewSet, basename="service")
router.register(
    "service-availability",
    HospitalServiceAvailabilityViewSet,
    basename="service-availability",
)
router.register("rooms", RoomViewSet, basename="room")
router.register("beds", BedViewSet, basename="bed")
router.register("resources", ResourceViewSet, basename="resource")
router.register("external-hospitals", ExternalHospitalViewSet, basename="external-hospital")
router.register(
    "external-hospital-specialties",
    ExternalHospitalSpecialtyViewSet,
    basename="external-hospital-specialty",
)
router.register(
    "external-hospital-services",
    ExternalHospitalServiceViewSet,
    basename="external-hospital-service",
)
router.register("external-specialists", ExternalSpecialistViewSet, basename="external-specialist")

app_name = "hospital"

urlpatterns = [
    path("hospital/profile/", HospitalProfileView.as_view(), name="profile"),
    path("hospital/dashboard/", HeadOfServiceDashboardView.as_view(), name="dashboard"),
    path("hospital/", include(router.urls)),
]
