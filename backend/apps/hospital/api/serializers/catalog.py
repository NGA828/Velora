from rest_framework import serializers

from apps.hospital.models import (
    ClinicalCondition,
    HospitalServiceAvailability,
    ServiceDefinition,
    Specialty,
    SpecialtyCondition,
)


class SpecialtySerializer(serializers.ModelSerializer):
    condition_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Specialty
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ClinicalConditionSerializer(serializers.ModelSerializer):
    specialty_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ClinicalCondition
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class SpecialtyConditionSerializer(serializers.ModelSerializer):
    specialty_name = serializers.CharField(source="specialty.name", read_only=True)
    condition_name = serializers.CharField(source="condition.name", read_only=True)
    condition_code = serializers.CharField(source="condition.code", read_only=True)

    class Meta:
        model = SpecialtyCondition
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ServiceDefinitionSerializer(serializers.ModelSerializer):
    department_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ServiceDefinition
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class HospitalServiceAvailabilitySerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = HospitalServiceAvailability
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
