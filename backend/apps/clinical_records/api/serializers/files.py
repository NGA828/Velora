from rest_framework import serializers

from apps.clinical_records.models import MedicalFile


class MedicalFileSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.get_full_name", read_only=True)
    medical_record_number = serializers.CharField(
        source="patient.medical_record_number", read_only=True
    )
    opened_by_name = serializers.CharField(source="opened_by.get_full_name", read_only=True)

    class Meta:
        model = MedicalFile
        fields = (
            "id",
            "patient",
            "patient_name",
            "medical_record_number",
            "file_number",
            "status",
            "opened_at",
            "opened_by_name",
        )
