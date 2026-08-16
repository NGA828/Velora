from .catalog import (
    ClinicalConditionViewSet,
    HospitalServiceAvailabilityViewSet,
    ServiceDefinitionViewSet,
    SpecialtyConditionViewSet,
    SpecialtyViewSet,
)
from .core import DepartmentViewSet, HeadOfServiceDashboardView, HospitalProfileView
from .external import (
    ExternalHospitalServiceViewSet,
    ExternalHospitalSpecialtyViewSet,
    ExternalHospitalViewSet,
    ExternalSpecialistViewSet,
)
from .resources import BedViewSet, ResourceViewSet, RoomViewSet

__all__ = [
    "BedViewSet",
    "ClinicalConditionViewSet",
    "DepartmentViewSet",
    "ExternalHospitalServiceViewSet",
    "ExternalHospitalSpecialtyViewSet",
    "ExternalHospitalViewSet",
    "ExternalSpecialistViewSet",
    "HeadOfServiceDashboardView",
    "HospitalProfileView",
    "HospitalServiceAvailabilityViewSet",
    "ResourceViewSet",
    "RoomViewSet",
    "ServiceDefinitionViewSet",
    "SpecialtyConditionViewSet",
    "SpecialtyViewSet",
]
