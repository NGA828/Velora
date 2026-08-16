from rest_framework import serializers

from apps.prescriptions.models import Medication


class MedicationSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = Medication
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
