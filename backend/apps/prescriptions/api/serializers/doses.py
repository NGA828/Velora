from django.utils import timezone
from rest_framework import serializers

from apps.prescriptions.models import MedicationDose, MedicationDoseEvent


class MedicationDoseEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True)

    class Meta:
        model = MedicationDoseEvent
        fields = (
            "id",
            "actor_name",
            "previous_status",
            "new_status",
            "occurred_at",
            "notes",
        )


class MedicationDoseSerializer(serializers.ModelSerializer):
    patient = serializers.UUIDField(
        source="prescription_item.prescription.patient.id", read_only=True
    )
    patient_name = serializers.CharField(
        source="prescription_item.prescription.patient.get_full_name", read_only=True
    )
    medical_record_number = serializers.CharField(
        source="prescription_item.prescription.patient.medical_record_number",
        read_only=True,
    )
    prescription = serializers.UUIDField(source="prescription_item.prescription.id", read_only=True)
    medication_name = serializers.CharField(
        source="prescription_item.medication.__str__", read_only=True
    )
    dose_amount = serializers.DecimalField(
        source="prescription_item.dose_amount",
        max_digits=10,
        decimal_places=3,
        read_only=True,
    )
    dose_unit = serializers.CharField(source="prescription_item.dose_unit", read_only=True)
    route = serializers.CharField(source="prescription_item.route", read_only=True)
    instructions = serializers.CharField(source="prescription_item.instructions", read_only=True)
    acted_by_name = serializers.CharField(
        source="acted_by.get_full_name", read_only=True, default=None
    )
    events = MedicationDoseEventSerializer(many=True, read_only=True)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = MedicationDose
        fields = "__all__"

    def get_is_overdue(self, dose) -> bool:
        return dose.status == MedicationDose.Status.PENDING and dose.scheduled_for < timezone.now()


class DoseOutcomeSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")
