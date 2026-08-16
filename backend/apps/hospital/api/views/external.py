from django.db.models import Count

from apps.hospital.api.serializers import (
    ExternalHospitalSerializer,
    ExternalHospitalServiceSerializer,
    ExternalHospitalSpecialtySerializer,
    ExternalSpecialistSerializer,
)
from apps.hospital.models import (
    ExternalHospital,
    ExternalHospitalService,
    ExternalHospitalSpecialty,
    ExternalSpecialist,
)

from .base import HospitalConfigurationViewSet


class ExternalHospitalViewSet(HospitalConfigurationViewSet):
    serializer_class = ExternalHospitalSerializer
    search_fields = ["name", "city", "region", "country", "phone", "transfer_email"]
    ordering_fields = ["name", "city", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = ExternalHospital.objects.annotate(
            specialty_count=Count("specialty_capabilities", distinct=True),
            service_count=Count("service_capabilities", distinct=True),
            specialist_count=Count("specialists", distinct=True),
        )
        active = self.request.query_params.get("is_active")
        if active in {"true", "false"}:
            queryset = queryset.filter(is_active=active == "true")
        return queryset


class ExternalHospitalSpecialtyViewSet(HospitalConfigurationViewSet):
    serializer_class = ExternalHospitalSpecialtySerializer
    search_fields = ["external_hospital__name", "specialty__name"]
    ordering_fields = ["external_hospital__name", "specialty__name", "availability_status"]
    ordering = ["external_hospital__name", "specialty__name"]

    def get_queryset(self):
        queryset = ExternalHospitalSpecialty.objects.select_related(
            "external_hospital", "specialty"
        )
        hospital = self.request.query_params.get("external_hospital")
        return queryset.filter(external_hospital_id=hospital) if hospital else queryset


class ExternalHospitalServiceViewSet(HospitalConfigurationViewSet):
    serializer_class = ExternalHospitalServiceSerializer
    search_fields = ["external_hospital__name", "service__name"]
    ordering_fields = ["external_hospital__name", "service__name", "availability_status"]
    ordering = ["external_hospital__name", "service__name"]

    def get_queryset(self):
        queryset = ExternalHospitalService.objects.select_related("external_hospital", "service")
        hospital = self.request.query_params.get("external_hospital")
        return queryset.filter(external_hospital_id=hospital) if hospital else queryset


class ExternalSpecialistViewSet(HospitalConfigurationViewSet):
    serializer_class = ExternalSpecialistSerializer
    search_fields = ["full_name", "external_hospital__name", "specialty__name", "email"]
    ordering_fields = ["full_name", "external_hospital__name", "specialty__name"]
    ordering = ["external_hospital__name", "full_name"]

    def get_queryset(self):
        queryset = ExternalSpecialist.objects.select_related("external_hospital", "specialty")
        hospital = self.request.query_params.get("external_hospital")
        return queryset.filter(external_hospital_id=hospital) if hospital else queryset
