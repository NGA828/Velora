from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.common.throttling import ActionScopedThrottleMixin
from apps.identity.models import UserRole
from apps.patients.models import Patient
from apps.patients.selectors import patients_visible_to
from apps.transfers.api.serializers import (
    TransferDecisionInputSerializer,
    TransferRequestCreateSerializer,
    TransferRequestSerializer,
    TransferSubmitSerializer,
)
from apps.transfers.models import TransferRecommendation, TransferRequest
from apps.transfers.permissions import TransferPermission
from apps.transfers.services import (
    create_transfer_request,
    decide_transfer,
    generate_recommendations,
    submit_to_guardian,
    suggest_transfer_requirements,
    transmit_medical_package,
)


def _service_error(exc):
    raise serializers.ValidationError({"detail": exc.messages}) from exc


def _full_queryset():
    return TransferRequest.objects.select_related(
        "patient",
        "care_episode",
        "requested_by",
        "decision_guardian__user",
        "selected_hospital",
    ).prefetch_related(
        "requirements__specialty",
        "requirements__service",
        "requirements__condition",
        Prefetch(
            "recommendations",
            queryset=TransferRecommendation.objects.select_related("external_hospital"),
        ),
        "status_events__actor",
        "transmissions__external_hospital",
    )


class TransferRequestViewSet(ActionScopedThrottleMixin, ReadOnlyModelViewSet):
    permission_classes = [TransferPermission]
    throttle_scope_by_action = {"send_package": "transfer_transmit"}

    def get_serializer_class(self):
        return (
            TransferRequestCreateSerializer
            if self.action == "create"
            else TransferRequestSerializer
        )

    def get_queryset(self):
        queryset = _full_queryset()
        if self.request.user.role == UserRole.DOCTOR:
            queryset = queryset.filter(
                requested_by=self.request.user,
                patient__in=patients_visible_to(self.request.user),
            )
        else:
            queryset = queryset.filter(decision_guardian__user=self.request.user)
        patient = self.request.query_params.get("patient")
        return queryset.filter(patient_id=patient) if patient else queryset

    def create(self, request, *args, **kwargs):
        serializer = TransferRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            patient = patients_visible_to(request.user).get(pk=data["patient"])
        except Patient.DoesNotExist as exc:
            raise NotFound("Patient not found in your assigned care list.") from exc
        try:
            transfer = create_transfer_request(
                patient=patient,
                doctor=request.user,
                guardian=data["guardian"],
                reason=data["reason"],
                clinical_summary=data["clinical_summary"],
                urgency=data["urgency"],
                requirements=data["requirements"],
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(
            TransferRequestSerializer(_full_queryset().get(pk=transfer.pk)).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="suggest-requirements")
    def suggest_requirements(self, request):
        """Suggest transfer requirements from the patient's medical file:
        conditions + mapped specialties derived from active diagnoses."""
        patient_id = request.query_params.get("patient")
        if not patient_id:
            raise serializers.ValidationError({"patient": "Select a patient."})
        patient = get_object_or_404(
            patients_visible_to(request.user).filter(
                medical_file__isnull=False,
            ),
            pk=patient_id,
        )
        return Response(
            {"suggestions": suggest_transfer_requirements(patient=patient)}
        )

    @action(detail=True, methods=["post"])
    def recommend(self, request, pk=None):
        try:
            generate_recommendations(
                transfer=self.get_object(), doctor=request.user, request=request
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(TransferRequestSerializer(_full_queryset().get(pk=pk)).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        serializer = TransferSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            submit_to_guardian(
                transfer=self.get_object(),
                hospital=serializer.validated_data["hospital"],
                doctor=request.user,
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(TransferRequestSerializer(_full_queryset().get(pk=pk)).data)

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        serializer = TransferDecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            decide_transfer(
                transfer=self.get_object(),
                guardian=request.user.patient_guard_profile,
                decision=serializer.validated_data["decision"],
                reason=serializer.validated_data["reason"],
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(TransferRequestSerializer(_full_queryset().get(pk=pk)).data)

    @action(detail=True, methods=["post"], url_path="send-package")
    def send_package(self, request, pk=None):
        try:
            transmit_medical_package(
                transfer=self.get_object(), doctor=request.user, request=request
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(TransferRequestSerializer(_full_queryset().get(pk=pk)).data)
