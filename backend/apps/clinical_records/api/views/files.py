from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.audit.models import MedicalRecordAccess
from apps.audit.services import record_medical_access
from apps.clinical_records.api.serializers import MedicalFileSerializer
from apps.clinical_records.models import MedicalFile
from apps.clinical_records.permissions import ClinicalRecordPermission
from apps.identity.models import UserRole
from apps.patients.models import GuardianAccess
from apps.patients.selectors import patients_visible_to


class MedicalFileViewSet(ReadOnlyModelViewSet):
    serializer_class = MedicalFileSerializer
    permission_classes = [ClinicalRecordPermission]

    def get_queryset(self):
        patient_queryset = patients_visible_to(self.request.user)
        if self.request.user.role == UserRole.PATIENT_GUARD:
            patient_queryset = patient_queryset.filter(
                guardian_accesses__guardian__user=self.request.user,
                guardian_accesses__status=GuardianAccess.Status.ACTIVE,
                guardian_accesses__can_view_medical_file=True,
            )
        queryset = MedicalFile.objects.filter(patient__in=patient_queryset).select_related(
            "patient", "opened_by"
        )
        patient_id = self.request.query_params.get("patient")
        return queryset.filter(patient_id=patient_id) if patient_id else queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        patient_id = request.query_params.get("patient")
        if patient_id:
            medical_file = self.get_queryset().filter(patient_id=patient_id).first()
            if medical_file:
                record_medical_access(
                    user=request.user,
                    patient=medical_file.patient,
                    object_type=medical_file._meta.label,
                    object_id=medical_file.id,
                    action=MedicalRecordAccess.Action.LIST,
                    request=request,
                )
        return response

    def retrieve(self, request, *args, **kwargs):
        medical_file = self.get_object()
        record_medical_access(
            user=request.user,
            patient=medical_file.patient,
            object_type=medical_file._meta.label,
            object_id=medical_file.id,
            action=MedicalRecordAccess.Action.VIEW,
            request=request,
        )
        return Response(self.get_serializer(medical_file).data)
