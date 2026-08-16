from rest_framework import serializers

from apps.hospital.models import (
    ExternalHospital,
    ExternalHospitalService,
    ExternalHospitalSpecialty,
    ExternalSpecialist,
)


class ExternalHospitalSerializer(serializers.ModelSerializer):
    specialty_count = serializers.IntegerField(read_only=True, default=0)
    service_count = serializers.IntegerField(read_only=True, default=0)
    specialist_count = serializers.IntegerField(read_only=True, default=0)
    transfer_ready = serializers.SerializerMethodField()

    class Meta:
        model = ExternalHospital
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def get_transfer_ready(self, hospital) -> bool:
        specialty_count = getattr(hospital, "specialty_count", 0)
        service_count = getattr(hospital, "service_count", 0)
        return bool(hospital.transfer_email and (specialty_count or service_count))

    def validate(self, attrs):
        latitude = attrs.get("latitude", getattr(self.instance, "latitude", None))
        longitude = attrs.get("longitude", getattr(self.instance, "longitude", None))
        if latitude is not None and not -90 <= latitude <= 90:
            raise serializers.ValidationError({"latitude": "Latitude must be between -90 and 90."})
        if longitude is not None and not -180 <= longitude <= 180:
            raise serializers.ValidationError(
                {"longitude": "Longitude must be between -180 and 180."}
            )
        return attrs


class ExternalHospitalSpecialtySerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source="external_hospital.name", read_only=True)
    specialty_name = serializers.CharField(source="specialty.name", read_only=True)

    class Meta:
        model = ExternalHospitalSpecialty
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ExternalHospitalServiceSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source="external_hospital.name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = ExternalHospitalService
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ExternalSpecialistSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source="external_hospital.name", read_only=True)
    specialty_name = serializers.CharField(source="specialty.name", read_only=True)

    class Meta:
        model = ExternalSpecialist
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
