from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.vital_signs.models import (
    VitalMetric,
    VitalObservation,
    VitalRuleEvaluation,
    VitalValue,
)


class VitalRuleEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalRuleEvaluation
        fields = (
            "id",
            "matched",
            "measured_value",
            "rule_name_snapshot",
            "metric_name_snapshot",
            "metric_unit_snapshot",
            "operator_snapshot",
            "lower_value_snapshot",
            "upper_value_snapshot",
            "explanation",
        )


class VitalValueSerializer(serializers.ModelSerializer):
    metric_name = serializers.CharField(source="metric.name", read_only=True)
    metric_code = serializers.CharField(source="metric.code", read_only=True)
    unit = serializers.CharField(source="metric.unit", read_only=True)
    contributes_to_assessment = serializers.BooleanField(
        source="metric.contributes_to_assessment", read_only=True
    )
    is_critical = serializers.SerializerMethodField()
    evaluations = VitalRuleEvaluationSerializer(many=True, read_only=True)

    class Meta:
        model = VitalValue
        fields = (
            "id",
            "metric",
            "metric_name",
            "metric_code",
            "unit",
            "value",
            "contributes_to_assessment",
            "is_critical",
            "evaluations",
        )

    def get_is_critical(self, obj) -> bool:
        return any(evaluation.matched for evaluation in obj.evaluations.all())


class VitalObservationSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.get_full_name", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.get_full_name", read_only=True)
    values = VitalValueSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = VitalObservation
        fields = (
            "id",
            "patient",
            "patient_name",
            "care_episode",
            "observed_at",
            "recorded_by_name",
            "status",
            "status_label",
            "stability_percent",
            "criticality_percent",
            "assessed_metric_count",
            "critical_metric_count",
            "notes",
            "analyzed_at",
            "rule_set_name_snapshot",
            "rule_set_version_snapshot",
            "values",
            "created_at",
        )


class VitalMeasurementInputSerializer(serializers.Serializer):
    metric = serializers.PrimaryKeyRelatedField(queryset=VitalMetric.objects.filter(is_active=True))
    value = serializers.DecimalField(max_digits=12, decimal_places=4)


class VitalObservationCreateSerializer(serializers.Serializer):
    patient = serializers.UUIDField()
    observed_at = serializers.DateTimeField(required=False, default=timezone.now)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    values = VitalMeasurementInputSerializer(many=True, allow_empty=False)

    def validate_observed_at(self, value):
        if value > timezone.now() + timedelta(minutes=5):
            raise serializers.ValidationError("Observation time cannot be in the future.")
        return value

    def validate_values(self, value):
        metric_ids = [item["metric"].id for item in value]
        if len(metric_ids) != len(set(metric_ids)):
            raise serializers.ValidationError("Record each vital metric only once.")
        return value
