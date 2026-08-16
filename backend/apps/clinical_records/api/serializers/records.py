from rest_framework import serializers

from apps.clinical_records.models import (
    Allergy,
    ClinicalNote,
    Diagnosis,
    MedicalHistoryEntry,
    TreatmentPlan,
)


class AllergySerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source="recorded_by.get_full_name", read_only=True)
    severity_label = serializers.CharField(source="get_severity_display", read_only=True)

    class Meta:
        model = Allergy
        fields = "__all__"
        read_only_fields = ("id", "recorded_by", "recorded_at", "created_at", "updated_at")


class MedicalHistoryEntrySerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source="recorded_by.get_full_name", read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = MedicalHistoryEntry
        fields = "__all__"
        read_only_fields = ("id", "recorded_by", "created_at", "updated_at")


class DiagnosisSerializer(serializers.ModelSerializer):
    diagnosed_by_name = serializers.CharField(source="diagnosed_by.get_full_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Diagnosis
        fields = "__all__"
        read_only_fields = (
            "id",
            "diagnosed_by",
            "code_snapshot",
            "name_snapshot",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {"diagnosed_at": {"required": False}}

    def validate(self, attrs):
        condition = attrs.get("condition", getattr(self.instance, "condition", None))
        if not condition:
            raise serializers.ValidationError(
                {"condition": "Select a configured clinical condition."}
            )
        episode = attrs.get("care_episode", getattr(self.instance, "care_episode", None))
        patient = attrs.get("patient", getattr(self.instance, "patient", None))
        if episode and patient and episode.patient_id != patient.id:
            raise serializers.ValidationError(
                {"care_episode": "The care episode does not belong to this patient."}
            )
        return attrs

    def create(self, validated_data):
        condition = validated_data["condition"]
        validated_data["code_snapshot"] = f"{condition.coding_system}:{condition.code}"
        validated_data["name_snapshot"] = condition.name
        return super().create(validated_data)

    def update(self, instance, validated_data):
        condition = validated_data.get("condition")
        if condition:
            validated_data["code_snapshot"] = f"{condition.coding_system}:{condition.code}"
            validated_data["name_snapshot"] = condition.name
        return super().update(instance, validated_data)


class TreatmentPlanSerializer(serializers.ModelSerializer):
    authored_by_name = serializers.CharField(source="authored_by.get_full_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TreatmentPlan
        fields = "__all__"
        read_only_fields = ("id", "authored_by", "created_at", "updated_at")

    def validate(self, attrs):
        starts_on = attrs.get("starts_on", getattr(self.instance, "starts_on", None))
        ends_on = attrs.get("ends_on", getattr(self.instance, "ends_on", None))
        if starts_on and ends_on and ends_on < starts_on:
            raise serializers.ValidationError(
                {"ends_on": "End date cannot be before the start date."}
            )
        episode = attrs.get("care_episode", getattr(self.instance, "care_episode", None))
        patient = attrs.get("patient", getattr(self.instance, "patient", None))
        if episode and patient and episode.patient_id != patient.id:
            raise serializers.ValidationError(
                {"care_episode": "The care episode does not belong to this patient."}
            )
        return attrs


class ClinicalNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.get_full_name", read_only=True)
    note_type_label = serializers.CharField(source="get_note_type_display", read_only=True)

    class Meta:
        model = ClinicalNote
        fields = "__all__"
        read_only_fields = (
            "id",
            "author",
            "status",
            "signed_at",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        episode = attrs.get("care_episode", getattr(self.instance, "care_episode", None))
        patient = attrs.get("patient", getattr(self.instance, "patient", None))
        if episode and patient and episode.patient_id != patient.id:
            raise serializers.ValidationError(
                {"care_episode": "The care episode does not belong to this patient."}
            )
        return attrs
