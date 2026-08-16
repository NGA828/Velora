from rest_framework import serializers

from apps.vital_signs.models import VitalMetric, VitalRule, VitalRuleSet


class VitalMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalMetric
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class VitalRuleSetSerializer(serializers.ModelSerializer):
    rule_count = serializers.IntegerField(read_only=True, default=0)
    approved_by_name = serializers.CharField(
        source="approved_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = VitalRuleSet
        fields = "__all__"
        read_only_fields = (
            "id",
            "status",
            "active_marker",
            "effective_from",
            "effective_to",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        )


class VitalRuleSerializer(serializers.ModelSerializer):
    metric_name = serializers.CharField(source="metric.name", read_only=True)
    metric_unit = serializers.CharField(source="metric.unit", read_only=True)
    rule_set_name = serializers.CharField(source="rule_set.name", read_only=True)
    operator_label = serializers.CharField(source="get_operator_display", read_only=True)

    class Meta:
        model = VitalRule
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        instance = self.instance
        rule_set = attrs.get("rule_set", getattr(instance, "rule_set", None))
        operator = attrs.get("operator", getattr(instance, "operator", None))
        lower = attrs.get("lower_value", getattr(instance, "lower_value", None))
        upper = attrs.get("upper_value", getattr(instance, "upper_value", None))

        if rule_set and rule_set.status != VitalRuleSet.Status.DRAFT:
            raise serializers.ValidationError(
                {"rule_set": "Rules can only be changed while the rule set is in draft."}
            )
        if operator in {VitalRule.Operator.BETWEEN, VitalRule.Operator.OUTSIDE}:
            if lower is None or upper is None:
                raise serializers.ValidationError("Range operators require lower and upper values.")
            if lower >= upper:
                raise serializers.ValidationError(
                    {"upper_value": "Upper value must be greater than lower value."}
                )
        elif operator in {
            VitalRule.Operator.LESS_THAN,
            VitalRule.Operator.LESS_THAN_OR_EQUAL,
        }:
            if upper is None:
                raise serializers.ValidationError(
                    {"upper_value": "This operator requires an upper value."}
                )
        elif lower is None:
            raise serializers.ValidationError(
                {"lower_value": "This operator requires a lower value."}
            )
        return attrs
