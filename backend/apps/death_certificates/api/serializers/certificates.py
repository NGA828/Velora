from django.utils import timezone
from rest_framework import serializers

from apps.death_certificates.models import DeathCertificate


class DeathCertificateSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.get_full_name", read_only=True)
    medical_record_number = serializers.CharField(
        source="patient.medical_record_number", read_only=True
    )
    date_of_birth = serializers.DateField(source="patient.date_of_birth", read_only=True)
    sex_at_birth = serializers.CharField(source="patient.sex_at_birth", read_only=True)
    issuing_doctor_name = serializers.CharField(
        source="issuing_doctor.get_full_name", read_only=True
    )

    class Meta:
        model = DeathCertificate
        fields = "__all__"


class DeathCertificateCreateSerializer(serializers.Serializer):
    patient = serializers.UUIDField()
    death_datetime = serializers.DateTimeField()
    place_of_death = serializers.CharField(max_length=180)
    primary_cause = serializers.CharField()
    contributing_causes = serializers.CharField(required=False, allow_blank=True, default="")
    manner_of_death = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_death_datetime(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("Death date and time cannot be in the future.")
        return value


class VoidCertificateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300)
