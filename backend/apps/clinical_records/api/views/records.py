from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.audit.models import MedicalRecordAccess
from apps.audit.services import record_audit_event, record_medical_access
from apps.clinical_records.api.serializers import (
    AllergySerializer,
    ClinicalNoteSerializer,
    DiagnosisSerializer,
    MedicalHistoryEntrySerializer,
    TreatmentPlanSerializer,
)
from apps.clinical_records.models import (
    Allergy,
    ClinicalNote,
    Diagnosis,
    GuardianVisibility,
    MedicalHistoryEntry,
    TreatmentPlan,
)
from apps.clinical_records.permissions import ClinicalRecordPermission
from apps.common.throttling import ActionScopedThrottleMixin
from apps.common.viewsets import AuditedNoDestroyModelViewSet
from apps.identity.models import UserRole
from apps.patients.selectors import patients_visible_to


class ClinicalRecordViewSet(ActionScopedThrottleMixin, AuditedNoDestroyModelViewSet):
    permission_classes = [ClinicalRecordPermission]
    throttle_scope_by_action = {
        "create": "clinical_write",
        "update": "clinical_write",
        "partial_update": "clinical_write",
        "sign": "clinical_write",
    }
    patient_field = "patient"

    def visible_patients(self):
        queryset = patients_visible_to(self.request.user)
        if self.request.user.role == UserRole.PATIENT_GUARD:
            queryset = queryset.filter(
                guardian_accesses__guardian__user=self.request.user,
                guardian_accesses__status="ACTIVE",
                guardian_accesses__can_view_medical_file=True,
            )
        return queryset

    def scope_queryset(self, queryset):
        queryset = queryset.filter(patient__in=self.visible_patients())
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        if self.request.user.role == UserRole.PATIENT_GUARD:
            queryset = queryset.filter(guardian_visibility=GuardianVisibility.GUARDIAN)
        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        patient_id = request.query_params.get("patient")
        if patient_id:
            patient = self.visible_patients().filter(pk=patient_id).first()
            if patient:
                record_medical_access(
                    user=request.user,
                    patient=patient,
                    object_type=self.get_queryset().model._meta.label,
                    action=MedicalRecordAccess.Action.LIST,
                    request=request,
                )
        return response

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        record_medical_access(
            user=request.user,
            patient=instance.patient,
            object_type=instance._meta.label,
            object_id=instance.pk,
            action=MedicalRecordAccess.Action.VIEW,
            request=request,
        )
        return Response(self.get_serializer(instance).data)

    def _validate_patient_write(self, serializer):
        patient = serializer.validated_data.get(
            "patient", getattr(serializer.instance, "patient", None)
        )
        if not patient or not self.visible_patients().filter(pk=patient.pk).exists():
            raise PermissionDenied("You do not have an active care assignment for this patient.")


class AllergyViewSet(ClinicalRecordViewSet):
    serializer_class = AllergySerializer

    def get_queryset(self):
        return self.scope_queryset(Allergy.objects.select_related("patient", "recorded_by"))

    def perform_create(self, serializer):
        self._validate_patient_write(serializer)
        serializer.validated_data["recorded_by"] = self.request.user
        serializer.validated_data["recorded_at"] = timezone.now()
        super().perform_create(serializer)


class MedicalHistoryEntryViewSet(ClinicalRecordViewSet):
    serializer_class = MedicalHistoryEntrySerializer

    def get_queryset(self):
        return self.scope_queryset(
            MedicalHistoryEntry.objects.select_related("patient", "recorded_by")
        )

    def perform_create(self, serializer):
        self._validate_patient_write(serializer)
        serializer.validated_data["recorded_by"] = self.request.user
        super().perform_create(serializer)


class DiagnosisViewSet(ClinicalRecordViewSet):
    serializer_class = DiagnosisSerializer

    def get_queryset(self):
        return self.scope_queryset(
            Diagnosis.objects.select_related("patient", "care_episode", "condition", "diagnosed_by")
        )

    def perform_create(self, serializer):
        if self.request.user.role != UserRole.DOCTOR:
            raise PermissionDenied("Only an assigned Doctor can record a diagnosis.")
        self._validate_patient_write(serializer)
        serializer.validated_data["diagnosed_by"] = self.request.user
        serializer.validated_data.setdefault("diagnosed_at", timezone.now())
        super().perform_create(serializer)

    def perform_update(self, serializer):
        if self.request.user.role != UserRole.DOCTOR:
            raise PermissionDenied("Only an assigned Doctor can update a diagnosis.")
        self._validate_patient_write(serializer)
        super().perform_update(serializer)


class TreatmentPlanViewSet(ClinicalRecordViewSet):
    serializer_class = TreatmentPlanSerializer

    def get_queryset(self):
        return self.scope_queryset(
            TreatmentPlan.objects.select_related("patient", "care_episode", "authored_by")
        )

    def perform_create(self, serializer):
        if self.request.user.role != UserRole.DOCTOR:
            raise PermissionDenied("Only an assigned Doctor can create a treatment plan.")
        self._validate_patient_write(serializer)
        serializer.validated_data["authored_by"] = self.request.user
        super().perform_create(serializer)

    def perform_update(self, serializer):
        if self.request.user.role != UserRole.DOCTOR:
            raise PermissionDenied("Only an assigned Doctor can update a treatment plan.")
        self._validate_patient_write(serializer)
        super().perform_update(serializer)


class ClinicalNoteViewSet(ClinicalRecordViewSet):
    serializer_class = ClinicalNoteSerializer

    def get_queryset(self):
        queryset = self.scope_queryset(
            ClinicalNote.objects.select_related("patient", "care_episode", "author")
        )
        if self.request.user.role == UserRole.PATIENT_GUARD:
            queryset = queryset.filter(status=ClinicalNote.Status.SIGNED)
        return queryset

    def perform_create(self, serializer):
        self._validate_patient_write(serializer)
        if (
            self.request.user.role == UserRole.NURSE
            and serializer.validated_data["note_type"] != ClinicalNote.NoteType.NURSING
        ):
            raise PermissionDenied("Nurses can create Nursing notes only.")
        serializer.validated_data["author"] = self.request.user
        super().perform_create(serializer)

    def perform_update(self, serializer):
        note = serializer.instance
        if note.status == ClinicalNote.Status.SIGNED:
            raise serializers.ValidationError("Signed notes are immutable; create an amendment.")
        if note.author_id != self.request.user.id:
            raise PermissionDenied("Only the note author can edit this draft.")
        self._validate_patient_write(serializer)
        super().perform_update(serializer)

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        note = self.get_object()
        if note.author_id != request.user.id:
            raise PermissionDenied("Only the note author can sign it.")
        if note.status == ClinicalNote.Status.SIGNED:
            raise serializers.ValidationError("This note is already signed.")
        note.status = ClinicalNote.Status.SIGNED
        note.signed_at = timezone.now()
        note.save(update_fields=["status", "signed_at", "updated_at"])
        record_audit_event(
            actor=request.user,
            request=request,
            action="clinical_records.clinicalnote.signed",
            object_type="clinical_records.ClinicalNote",
            object_id=note.id,
            after={"status": note.status, "signed_at": note.signed_at.isoformat()},
        )
        return Response(self.get_serializer(note).data)
