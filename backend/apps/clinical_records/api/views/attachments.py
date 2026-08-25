import hashlib

from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.audit.models import MedicalRecordAccess
from apps.audit.services import record_medical_access
from apps.clinical_records.api.serializers import MedicalFileAttachmentSerializer
from apps.clinical_records.models import MedicalFile, MedicalFileAttachment
from apps.clinical_records.permissions import ClinicalRecordPermission
from apps.identity.models import UserRole
from apps.patients.models import GuardianAccess
from apps.patients.selectors import patients_visible_to

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class MedicalFileAttachmentViewSet(ReadOnlyModelViewSet):
    """Documents attached to a patient's medical file. Clinicians (Doctor,
    Nurse) can upload; everyone who can see the medical file can list and
    download. Downloads are audit-logged like other medical-record access."""

    serializer_class = MedicalFileAttachmentSerializer
    permission_classes = [ClinicalRecordPermission]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        patient_queryset = patients_visible_to(self.request.user)
        if self.request.user.role == UserRole.PATIENT_GUARD:
            patient_queryset = patient_queryset.filter(
                guardian_accesses__guardian__user=self.request.user,
                guardian_accesses__status=GuardianAccess.Status.ACTIVE,
                guardian_accesses__can_view_medical_file=True,
            )
        queryset = MedicalFileAttachment.objects.filter(
            patient__in=patient_queryset
        ).select_related("patient", "uploaded_by", "medical_file")
        patient_id = self.request.query_params.get("patient")
        return queryset.filter(patient_id=patient_id) if patient_id else queryset

    def create(self, request, *args, **kwargs):
        if request.user.role not in {UserRole.DOCTOR, UserRole.NURSE}:
            raise PermissionDenied("Only clinical staff can attach documents.")
        patient_id = request.data.get("patient")
        if not patient_id:
            raise NotFound("Select a patient.")
        patient = patients_visible_to(request.user).filter(pk=patient_id).first()
        if not patient:
            raise NotFound("Patient not found in your care list.")
        medical_file = MedicalFile.objects.filter(patient=patient).first()
        if not medical_file:
            raise NotFound("This patient has no medical file yet.")
        uploaded = request.FILES.get("file")
        if not uploaded:
            raise NotFound("Attach a document to upload.")
        if uploaded.size > MAX_ATTACHMENT_BYTES:
            raise ValidationError("Attachments must be 10 MB or smaller.")
        if uploaded.content_type not in ALLOWED_MIME_TYPES:
            raise ValidationError("Use a PDF, image, text or Word document.")
        checksum = hashlib.sha256(uploaded.read()).hexdigest()
        uploaded.seek(0)
        attachment = MedicalFileAttachment.objects.create(
            medical_file=medical_file,
            patient=patient,
            uploaded_by=request.user,
            file=uploaded,
            original_name=uploaded.name,
            mime_type=uploaded.content_type,
            byte_size=uploaded.size,
            checksum=checksum,
            description=str(request.data.get("description") or "")[:300],
        )
        record_medical_access(
            user=request.user,
            patient=patient,
            object_type=attachment._meta.label,
            object_id=attachment.id,
            action=MedicalRecordAccess.Action.ATTACH,
            purpose="Medical file document",
            request=request,
        )
        return Response(
            MedicalFileAttachmentSerializer(attachment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        attachment = self.get_object()
        record_medical_access(
            user=request.user,
            patient=attachment.patient,
            object_type=attachment._meta.label,
            object_id=attachment.id,
            action=MedicalRecordAccess.Action.VIEW,
            purpose="Medical file document download",
            request=request,
        )
        return FileResponse(
            attachment.file.open("rb"),
            content_type=attachment.mime_type,
            as_attachment=True,
            filename=attachment.original_name,
        )

    def destroy(self, request, *args, **kwargs):
        attachment = self.get_object()
        if request.user.role not in {UserRole.DOCTOR, UserRole.NURSE}:
            raise PermissionDenied("Only clinical staff can remove documents.")
        if attachment.uploaded_by != request.user:
            raise PermissionDenied("You can only remove documents you uploaded.")
        attachment.file.delete(save=False)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
