from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.common.throttling import ActionScopedThrottleMixin
from apps.common.viewsets import AuditedNoDestroyModelViewSet
from apps.identity.models import UserRole
from apps.patients.api.serializers import (
    GuardianAccessSerializer,
    GuardianInvitationSerializer,
    NurseAssignmentSerializer,
    PatientDetailSerializer,
    PatientListSerializer,
    PatientRegistrationSerializer,
    PatientUpdateSerializer,
)
from apps.patients.models import GuardianAccess
from apps.patients.permissions import PatientAccessPermission
from apps.patients.selectors import patients_visible_to
from apps.patients.services import (
    assign_primary_nurse,
    invite_patient_guard,
    register_patient,
    revoke_guardian_access,
)


def _service_validation(exc: DjangoValidationError):
    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(exc.message_dict) from exc
    raise serializers.ValidationError({"detail": exc.messages}) from exc


class PatientViewSet(ActionScopedThrottleMixin, AuditedNoDestroyModelViewSet):
    permission_classes = [PatientAccessPermission]
    throttle_scope_by_action = {
        "create": "patient_registration",
        "assign_nurse": "clinical_write",
        "guardians": "clinical_write",
        "revoke_guardian": "clinical_write",
    }
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["medical_record_number", "first_name", "last_name"]
    ordering_fields = ["created_at", "last_name", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return patients_visible_to(self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return PatientRegistrationSerializer
        if self.action in {"update", "partial_update"}:
            return PatientUpdateSerializer
        if self.action == "list":
            return PatientListSerializer
        return PatientDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = PatientRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            patient = register_patient(
                doctor=request.user,
                assigned_nurse=data["assigned_nurse"],
                department=data["department"],
                patient_data=serializer.patient_data(),
                episode_type=data["episode_type"],
                admission_reason=data["admission_reason"],
                request=request,
            )
        except DjangoValidationError as exc:
            _service_validation(exc)
        patient = patients_visible_to(request.user).get(pk=patient.pk)
        return Response(PatientDetailSerializer(patient).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="assign-nurse")
    def assign_nurse(self, request, pk=None):
        patient = self.get_object()
        serializer = NurseAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            assign_primary_nurse(
                patient=patient,
                nurse=serializer.validated_data["nurse"],
                doctor=request.user,
                request=request,
            )
        except DjangoValidationError as exc:
            _service_validation(exc)
        refreshed = patients_visible_to(request.user).get(pk=patient.pk)
        return Response(PatientDetailSerializer(refreshed).data)

    @action(detail=True, methods=["get", "post"])
    def guardians(self, request, pk=None):
        patient = self.get_object()
        if request.method == "GET":
            accesses = patient.guardian_accesses.select_related("guardian__user", "invitation")
            return Response(GuardianAccessSerializer(accesses, many=True).data)
        if request.user.role != UserRole.NURSE:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only an assigned Nurse can invite a Patient Guard.")
        serializer = GuardianInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            access = invite_patient_guard(
                patient=patient,
                nurse=request.user,
                email=serializer.validated_data["email"],
                relationship=serializer.validated_data["relationship"],
                permissions=serializer.validated_data,
                request=request,
            )
        except DjangoValidationError as exc:
            _service_validation(exc)
        return Response(GuardianAccessSerializer(access).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"guardians/(?P<access_id>[^/.]+)/revoke",
    )
    def revoke_guardian(self, request, pk=None, access_id=None):
        patient = self.get_object()
        if request.user.role != UserRole.NURSE:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only an assigned Nurse can revoke Patient Guard access.")
        try:
            access = patient.guardian_accesses.get(pk=access_id)
        except GuardianAccess.DoesNotExist as exc:
            from rest_framework.exceptions import NotFound

            raise NotFound("Patient Guard access not found.") from exc
        try:
            access = revoke_guardian_access(access=access, actor=request.user, request=request)
        except DjangoValidationError as exc:
            _service_validation(exc)
        return Response(GuardianAccessSerializer(access).data)

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        queryset = self.get_queryset()
        total = queryset.count()
        without_guard = queryset.filter(active_guardian_count=0).count()
        by_status = {
            item["status"]: item["count"]
            for item in queryset.values("status").annotate(count=Count("id"))
        }
        return Response(
            {
                "role": request.user.role,
                "total_assigned": total,
                "active_episodes": queryset.filter(care_episodes__status="ACTIVE")
                .distinct()
                .count(),
                "without_guard": without_guard,
                "critical_patients": queryset.filter(latest_vital_status="CRITICAL").count(),
                "unassessed_patients": queryset.filter(latest_vital_status="UNASSESSED").count(),
                "by_status": by_status,
                "recent_patients": PatientListSerializer(queryset[:5], many=True).data,
            }
        )
