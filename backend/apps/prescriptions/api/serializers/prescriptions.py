from django.utils import timezone
from rest_framework import serializers

from apps.prescriptions.models import (
    DoseScheduleRule,
    Medication,
    MedicationDose,
    Prescription,
    PrescriptionItem,
)


class DoseScheduleRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoseScheduleRule
        fields = ("id", "local_time", "days_of_week", "timezone")


class PrescriptionItemSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(source="medication.__str__", read_only=True)
    schedule_rules = DoseScheduleRuleSerializer(many=True, read_only=True)

    class Meta:
        model = PrescriptionItem
        fields = "__all__"


class PrescriptionSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.get_full_name", read_only=True)
    medical_record_number = serializers.CharField(
        source="patient.medical_record_number", read_only=True
    )
    prescribed_by_name = serializers.CharField(source="prescribed_by.get_full_name", read_only=True)
    items = PrescriptionItemSerializer(many=True, read_only=True)
    dose_summary = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = "__all__"

    def get_dose_summary(self, prescription) -> dict:
        doses = [dose for item in prescription.items.all() for dose in item.doses.all()]
        summary = {status: 0 for status, _ in MedicationDose.Status.choices}
        for dose in doses:
            summary[dose.status] = summary.get(dose.status, 0) + 1
        return summary


class ScheduleTimeInputSerializer(serializers.Serializer):
    local_time = serializers.TimeField()
    days_of_week = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        required=False,
        default=list,
    )


class PrescriptionItemInputSerializer(serializers.Serializer):
    medication = serializers.PrimaryKeyRelatedField(
        queryset=Medication.objects.filter(is_active=True)
    )
    dose_amount = serializers.DecimalField(max_digits=10, decimal_places=3)
    dose_unit = serializers.CharField(max_length=32)
    route = serializers.ChoiceField(choices=PrescriptionItem.Route.choices)
    frequency_display = serializers.CharField(max_length=120)
    duration_days = serializers.IntegerField(min_value=1, max_value=366)
    instructions = serializers.CharField(required=False, allow_blank=True, default="")
    schedule_type = serializers.ChoiceField(
        choices=PrescriptionItem.ScheduleType.choices,
        default=PrescriptionItem.ScheduleType.SCHEDULED,
    )
    prn_max_per_day = serializers.IntegerField(
        min_value=1,
        max_value=24,
        required=False,
        allow_null=True,
    )
    schedule_times = ScheduleTimeInputSerializer(many=True, required=False, default=list)

    def validate(self, attrs):
        if (
            attrs["schedule_type"] == PrescriptionItem.ScheduleType.SCHEDULED
            and not attrs["schedule_times"]
        ):
            raise serializers.ValidationError(
                {"schedule_times": "Add at least one scheduled dose time."}
            )
        if attrs["schedule_type"] == PrescriptionItem.ScheduleType.PRN and not attrs.get(
            "prn_max_per_day"
        ):
            raise serializers.ValidationError(
                {"prn_max_per_day": "Set the maximum daily PRN administrations."}
            )
        local_times = [item["local_time"] for item in attrs["schedule_times"]]
        if len(local_times) != len(set(local_times)):
            raise serializers.ValidationError(
                {"schedule_times": "Dose times must be unique for each medication."}
            )
        return attrs


class PrescriptionCreateSerializer(serializers.Serializer):
    patient = serializers.UUIDField()
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    clinical_instructions = serializers.CharField(required=False, allow_blank=True, default="")
    items = PrescriptionItemInputSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        if attrs["ends_on"] < attrs["starts_on"]:
            raise serializers.ValidationError(
                {"ends_on": "End date cannot be before the start date."}
            )
        if attrs["starts_on"] < timezone.localdate():
            raise serializers.ValidationError(
                {"starts_on": "A new prescription cannot start in the past."}
            )
        span = (attrs["ends_on"] - attrs["starts_on"]).days + 1
        for index, item in enumerate(attrs["items"]):
            if item["duration_days"] > span:
                raise serializers.ValidationError(
                    {"items": {index: "Item duration exceeds the prescription date range."}}
                )
        return attrs

    def service_items(self) -> list[dict]:
        result = []
        for validated in self.validated_data["items"]:
            item = dict(validated)
            item["schedules"] = item.pop("schedule_times")
            result.append(item)
        return result


class PrescriptionCancellationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300)
