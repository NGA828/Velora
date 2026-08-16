from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.audit.models import MedicalRecordAccess
from apps.audit.services import record_medical_access
from apps.death_certificates.api.serializers import (
    DeathCertificateCreateSerializer,
    DeathCertificateSerializer,
    VoidCertificateSerializer,
)
from apps.death_certificates.models import DeathCertificate
from apps.death_certificates.permissions import DeathCertificatePermission
from apps.death_certificates.services import (
    create_certificate,
    issue_certificate,
    void_certificate,
)
from apps.identity.models import UserRole
from apps.patients.models import GuardianAccess, Patient
from apps.patients.selectors import patients_visible_to


def _service_error(exc):
    raise serializers.ValidationError({"detail": exc.messages}) from exc


class DeathCertificateViewSet(ReadOnlyModelViewSet):
    permission_classes = [DeathCertificatePermission]

    def get_serializer_class(self):
        return (
            DeathCertificateCreateSerializer
            if self.action == "create"
            else DeathCertificateSerializer
        )

    def get_queryset(self):
        queryset = DeathCertificate.objects.select_related("patient", "issuing_doctor")
        if self.request.user.role == UserRole.DOCTOR:
            queryset = queryset.filter(
                Q(issuing_doctor=self.request.user)
                | Q(patient__in=patients_visible_to(self.request.user))
            ).distinct()
        else:
            queryset = queryset.filter(
                status=DeathCertificate.Status.ISSUED,
                patient__guardian_accesses__guardian__user=self.request.user,
                patient__guardian_accesses__status=GuardianAccess.Status.ACTIVE,
            ).distinct()
        patient = self.request.query_params.get("patient")
        return queryset.filter(patient_id=patient) if patient else queryset

    def create(self, request, *args, **kwargs):
        serializer = DeathCertificateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            patient = patients_visible_to(request.user).get(pk=data.pop("patient"))
        except Patient.DoesNotExist as exc:
            raise NotFound("Patient not found in your assigned care list.") from exc
        try:
            certificate = create_certificate(
                patient=patient, doctor=request.user, data=data, request=request
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(
            DeathCertificateSerializer(certificate).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        try:
            certificate = issue_certificate(
                certificate=self.get_object(), doctor=request.user, request=request
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(DeathCertificateSerializer(certificate).data)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        serializer = VoidCertificateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            certificate = void_certificate(
                certificate=self.get_object(),
                doctor=request.user,
                reason=serializer.validated_data["reason"],
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(DeathCertificateSerializer(certificate).data)

    def retrieve(self, request, *args, **kwargs):
        certificate = self.get_object()
        record_medical_access(
            user=request.user,
            patient=certificate.patient,
            object_type=certificate._meta.label,
            object_id=certificate.id,
            action=MedicalRecordAccess.Action.VIEW,
            request=request,
        )
        return Response(DeathCertificateSerializer(certificate).data)

    @action(detail=True, methods=["get"])
    def printable(self, request, pk=None):
        certificate = self.get_object()
        if certificate.status != DeathCertificate.Status.ISSUED:
            raise NotFound("Only issued certificates are printable.")
        record_medical_access(
            user=request.user,
            patient=certificate.patient,
            object_type=certificate._meta.label,
            object_id=certificate.id,
            action=MedicalRecordAccess.Action.PRINT,
            request=request,
        )
        return Response(DeathCertificateSerializer(certificate).data)
