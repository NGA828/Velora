from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.common.throttling import ActionScopedThrottleMixin
from apps.identity.models import UserRole
from apps.patients.models import Patient
from apps.patients.selectors import patients_visible_to
from apps.vital_signs.api.serializers import (
    VitalObservationCreateSerializer,
    VitalObservationSerializer,
)
from apps.vital_signs.models import VitalObservation, VitalRuleEvaluation, VitalValue
from apps.vital_signs.permissions import VitalObservationPermission
from apps.vital_signs.services import record_and_analyze_observation


class VitalObservationViewSet(ActionScopedThrottleMixin, ReadOnlyModelViewSet):
    permission_classes = [VitalObservationPermission]
    throttle_scope_by_action = {"create": "clinical_write"}

    def get_serializer_class(self):
        return (
            VitalObservationCreateSerializer
            if self.action == "create"
            else VitalObservationSerializer
        )

    def get_queryset(self):
        values = VitalValue.objects.select_related("metric").prefetch_related(
            Prefetch(
                "evaluations",
                queryset=VitalRuleEvaluation.objects.select_related("rule"),
            )
        )
        queryset = (
            VitalObservation.objects.filter(patient__in=patients_visible_to(self.request.user))
            .select_related("patient", "care_episode", "recorded_by", "rule_set", "icu_recommendation")
            .prefetch_related(Prefetch("values", queryset=values))
        )
        patient = self.request.query_params.get("patient")
        if patient:
            queryset = queryset.filter(patient_id=patient)
        observation_status = self.request.query_params.get("status")
        if observation_status:
            queryset = queryset.filter(status=observation_status)
        return queryset

    @action(detail=False, methods=["get"], url_path="icu-recommendations")
    def icu_recommendations(self, request, *args, **kwargs):
        """Feed of AI decision-support recommendations for the caller's visible
        patients, newest first — the surface where clinicians see the ICU
        recommendation system's output."""
        queryset = self.get_queryset().filter(icu_recommendation__isnull=False).order_by(
            "-icu_recommendation__generated_at"
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(
                self.get_serializer(page, many=True).data
            )
        return Response(self.get_serializer(queryset, many=True).data)

    def create(self, request, *args, **kwargs):
        if request.user.role != UserRole.NURSE:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only an assigned Nurse can record vital signs.")
        serializer = VitalObservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            patient = patients_visible_to(request.user).get(pk=data["patient"])
        except Patient.DoesNotExist as exc:
            raise NotFound("Patient not found in your assigned care list.") from exc
        try:
            observation = record_and_analyze_observation(
                patient=patient,
                nurse=request.user,
                observed_at=data["observed_at"],
                values=data["values"],
                notes=data["notes"],
                request=request,
            )
        except DjangoValidationError as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict) from exc
            raise serializers.ValidationError({"detail": exc.messages}) from exc
        observation = self.get_queryset().get(pk=observation.pk)
        return Response(
            VitalObservationSerializer(observation).data,
            status=status.HTTP_201_CREATED,
        )
