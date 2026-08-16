from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.viewsets import AuditedNoDestroyModelViewSet
from apps.vital_signs.api.serializers import (
    VitalMetricSerializer,
    VitalRuleSerializer,
    VitalRuleSetSerializer,
)
from apps.vital_signs.models import VitalMetric, VitalRule, VitalRuleSet
from apps.vital_signs.permissions import VitalRuleConfigurationPermission
from apps.vital_signs.services import activate_rule_set, retire_rule_set


class VitalConfigurationViewSet(AuditedNoDestroyModelViewSet):
    permission_classes = [VitalRuleConfigurationPermission]


class VitalMetricViewSet(VitalConfigurationViewSet):
    serializer_class = VitalMetricSerializer
    queryset = VitalMetric.objects.all()


class VitalRuleSetViewSet(VitalConfigurationViewSet):
    serializer_class = VitalRuleSetSerializer

    def get_queryset(self):
        return VitalRuleSet.objects.select_related("approved_by").annotate(
            rule_count=Count("rules", filter=Q(rules__is_active=True), distinct=True)
        )

    def perform_update(self, serializer):
        if serializer.instance.status != VitalRuleSet.Status.DRAFT:
            raise serializers.ValidationError("Only a draft rule set can be edited.")
        super().perform_update(serializer)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        try:
            rule_set = activate_rule_set(
                rule_set=self.get_object(), actor=request.user, request=request
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"detail": exc.messages}) from exc
        return Response(VitalRuleSetSerializer(rule_set).data)

    @action(detail=True, methods=["post"])
    def retire(self, request, pk=None):
        try:
            rule_set = retire_rule_set(
                rule_set=self.get_object(), actor=request.user, request=request
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"detail": exc.messages}) from exc
        return Response(VitalRuleSetSerializer(rule_set).data)


class VitalRuleViewSet(VitalConfigurationViewSet):
    serializer_class = VitalRuleSerializer

    def get_queryset(self):
        queryset = VitalRule.objects.select_related("rule_set", "metric")
        rule_set = self.request.query_params.get("rule_set")
        return queryset.filter(rule_set_id=rule_set) if rule_set else queryset
