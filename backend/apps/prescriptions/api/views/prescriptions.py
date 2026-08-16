from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.identity.models import UserRole
from apps.patients.models import Patient
from apps.patients.selectors import patients_visible_to
from apps.prescriptions.api.serializers import (
    DoseOutcomeSerializer,
    MedicationDoseSerializer,
    PrescriptionCancellationSerializer,
    PrescriptionCreateSerializer,
    PrescriptionSerializer,
)
from apps.prescriptions.models import MedicationDose, Prescription, PrescriptionItem
from apps.prescriptions.permissions import PrescriptionPermission
from apps.prescriptions.selectors import doses_visible_to, prescriptions_visible_to
from apps.prescriptions.services import (
    activate_prescription,
    cancel_prescription,
    complete_prescription,
    create_prescription,
    record_dose_outcome,
)


def _service_error(exc: DjangoValidationError):
    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(exc.message_dict) from exc
    raise serializers.ValidationError({"detail": exc.messages}) from exc


def _prescription_queryset(user):
    doses = MedicationDose.objects.prefetch_related("events__actor")
    items = PrescriptionItem.objects.select_related("medication").prefetch_related(
        "schedule_rules", Prefetch("doses", queryset=doses)
    )
    return (
        prescriptions_visible_to(user)
        .select_related("patient", "care_episode", "prescribed_by")
        .prefetch_related(Prefetch("items", queryset=items))
    )


class PrescriptionViewSet(ReadOnlyModelViewSet):
    permission_classes = [PrescriptionPermission]

    def get_serializer_class(self):
        return PrescriptionCreateSerializer if self.action == "create" else PrescriptionSerializer

    def get_queryset(self):
        queryset = _prescription_queryset(self.request.user)
        patient = self.request.query_params.get("patient")
        if patient:
            queryset = queryset.filter(patient_id=patient)
        prescription_status = self.request.query_params.get("status")
        if prescription_status:
            queryset = queryset.filter(status=prescription_status)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = PrescriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            patient = patients_visible_to(request.user).get(pk=data["patient"])
        except Patient.DoesNotExist as exc:
            raise NotFound("Patient not found in your assigned care list.") from exc
        try:
            prescription = create_prescription(
                doctor=request.user,
                patient=patient,
                starts_on=data["starts_on"],
                ends_on=data["ends_on"],
                clinical_instructions=data["clinical_instructions"],
                items=serializer.service_items(),
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        prescription = _prescription_queryset(request.user).get(pk=prescription.pk)
        return Response(
            PrescriptionSerializer(prescription).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        try:
            prescription = activate_prescription(
                prescription=self.get_object(), doctor=request.user, request=request
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(
            PrescriptionSerializer(
                _prescription_queryset(request.user).get(pk=prescription.pk)
            ).data
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        serializer = PrescriptionCancellationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            prescription = cancel_prescription(
                prescription=self.get_object(),
                doctor=request.user,
                reason=serializer.validated_data["reason"],
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(
            PrescriptionSerializer(
                _prescription_queryset(request.user).get(pk=prescription.pk)
            ).data
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        try:
            prescription = complete_prescription(
                prescription=self.get_object(), doctor=request.user, request=request
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(
            PrescriptionSerializer(
                _prescription_queryset(request.user).get(pk=prescription.pk)
            ).data
        )


class MedicationDoseViewSet(ReadOnlyModelViewSet):
    serializer_class = MedicationDoseSerializer
    permission_classes = [PrescriptionPermission]

    def get_queryset(self):
        queryset = (
            doses_visible_to(self.request.user)
            .select_related(
                "prescription_item__medication",
                "prescription_item__prescription__patient",
                "acted_by",
            )
            .prefetch_related("events__actor")
        )
        patient = self.request.query_params.get("patient")
        if patient:
            queryset = queryset.filter(prescription_item__prescription__patient_id=patient)
        dose_status = self.request.query_params.get("status")
        if dose_status:
            queryset = queryset.filter(status=dose_status)
        return queryset

    @action(detail=False, methods=["get"])
    def due(self, request):
        if request.user.role != UserRole.NURSE:
            raise PermissionDenied("Only Nurses have a medication due queue.")
        queryset = self.get_queryset().filter(
            status=MedicationDose.Status.PENDING,
            scheduled_for__lte=timezone.now() + timedelta(hours=24),
            prescription_item__prescription__status=Prescription.Status.ACTIVE,
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(queryset, many=True).data)

    def _outcome(self, request, outcome):
        serializer = DoseOutcomeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            dose = record_dose_outcome(
                dose=self.get_object(),
                nurse=request.user,
                outcome=outcome,
                notes=serializer.validated_data["notes"],
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(self.get_serializer(self.get_queryset().get(pk=dose.pk)).data)

    @action(detail=True, methods=["post"])
    def administer(self, request, pk=None):
        return self._outcome(request, MedicationDose.Status.ADMINISTERED)

    @action(detail=True, methods=["post"])
    def miss(self, request, pk=None):
        return self._outcome(request, MedicationDose.Status.MISSED)

    @action(detail=True, methods=["post"])
    def refuse(self, request, pk=None):
        return self._outcome(request, MedicationDose.Status.REFUSED)
