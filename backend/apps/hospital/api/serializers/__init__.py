from .catalog import (
    ClinicalConditionSerializer,
    HospitalServiceAvailabilitySerializer,
    ServiceDefinitionSerializer,
    SpecialtyConditionSerializer,
    SpecialtySerializer,
)
from .core import DepartmentSerializer, HospitalProfileSerializer
from .external import (
    ExternalHospitalSerializer,
    ExternalHospitalServiceSerializer,
    ExternalHospitalSpecialtySerializer,
    ExternalSpecialistSerializer,
)
from .resources import BedSerializer, ResourceSerializer, RoomSerializer

__all__ = [
    "BedSerializer",
    "ClinicalConditionSerializer",
    "DepartmentSerializer",
    "ExternalHospitalSerializer",
    "ExternalHospitalServiceSerializer",
    "ExternalHospitalSpecialtySerializer",
    "ExternalSpecialistSerializer",
    "HospitalProfileSerializer",
    "HospitalServiceAvailabilitySerializer",
    "ResourceSerializer",
    "RoomSerializer",
    "ServiceDefinitionSerializer",
    "SpecialtyConditionSerializer",
    "SpecialtySerializer",
]
