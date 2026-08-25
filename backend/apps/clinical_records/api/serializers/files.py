from django.urls import reverse
from rest_framework import serializers

from apps.clinical_records.models import MedicalFile, MedicalFileAttachment


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


class MedicalFileAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.get_full_name", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = MedicalFileAttachment
        fields = (
            "id",
            "patient",
            "original_name",
            "mime_type",
            "byte_size",
            "checksum",
            "description",
            "uploaded_by_name",
            "uploaded_at",
            "download_url",
        )
        read_only_fields = fields

    def get_download_url(self, attachment) -> str | None:
        return reverse(
            "clinical_records:medical-file-attachment-download",
            args=[attachment.id],
        )
