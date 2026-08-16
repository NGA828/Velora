from django.db.models import Count

from apps.hospital.api.serializers import (
    ClinicalConditionSerializer,
    HospitalServiceAvailabilitySerializer,
    ServiceDefinitionSerializer,
    SpecialtyConditionSerializer,
    SpecialtySerializer,
)
from apps.hospital.models import (
    ClinicalCondition,
    HospitalServiceAvailability,
    ServiceDefinition,
    Specialty,
    SpecialtyCondition,
)

from .base import HospitalConfigurationViewSet


class SpecialtyViewSet(HospitalConfigurationViewSet):
    serializer_class = SpecialtySerializer
    search_fields = ["code", "name", "description"]
    ordering_fields = ["code", "name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = Specialty.objects.annotate(
            condition_count=Count("condition_mappings", distinct=True)
        )
        active = self.request.query_params.get("is_active")
        return (
            queryset.filter(is_active=active == "true") if active in {"true", "false"} else queryset
        )


class ClinicalConditionViewSet(HospitalConfigurationViewSet):
    serializer_class = ClinicalConditionSerializer
    search_fields = ["coding_system", "code", "name"]
    ordering_fields = ["coding_system", "code", "name"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = ClinicalCondition.objects.annotate(
            specialty_count=Count("specialty_mappings", distinct=True)
        )
        active = self.request.query_params.get("is_active")
        return (
            queryset.filter(is_active=active == "true") if active in {"true", "false"} else queryset
        )


class SpecialtyConditionViewSet(HospitalConfigurationViewSet):
    serializer_class = SpecialtyConditionSerializer
    search_fields = ["specialty__name", "condition__name", "condition__code"]
    ordering_fields = ["specialty__name", "condition__name", "match_weight"]
    ordering = ["specialty__name", "condition__name"]

    def get_queryset(self):
        queryset = SpecialtyCondition.objects.select_related("specialty", "condition")
        specialty = self.request.query_params.get("specialty")
        if specialty:
            queryset = queryset.filter(specialty_id=specialty)
        condition = self.request.query_params.get("condition")
        if condition:
            queryset = queryset.filter(condition_id=condition)
        return queryset


class ServiceDefinitionViewSet(HospitalConfigurationViewSet):
    serializer_class = ServiceDefinitionSerializer
    search_fields = ["code", "name", "category"]
    ordering_fields = ["code", "name", "category"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = ServiceDefinition.objects.annotate(
            department_count=Count("hospital_availability", distinct=True)
        )
        active = self.request.query_params.get("is_active")
        return (
            queryset.filter(is_active=active == "true") if active in {"true", "false"} else queryset
        )


class HospitalServiceAvailabilityViewSet(HospitalConfigurationViewSet):
    serializer_class = HospitalServiceAvailabilitySerializer
    search_fields = ["service__name", "department__name"]
    ordering_fields = ["service__name", "department__name", "availability_status"]
    ordering = ["service__name", "department__name"]

    def get_queryset(self):
        queryset = HospitalServiceAvailability.objects.select_related("service", "department")
        department = self.request.query_params.get("department")
        if department:
            queryset = queryset.filter(department_id=department)
        service = self.request.query_params.get("service")
        if service:
            queryset = queryset.filter(service_id=service)
        return queryset
