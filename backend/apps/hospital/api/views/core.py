from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_audit_event
from apps.hospital.api.serializers import DepartmentSerializer, HospitalProfileSerializer
from apps.hospital.models import (
    Bed,
    Department,
    ExternalHospital,
    HospitalProfile,
    Resource,
)
from apps.hospital.permissions import HeadOfServiceOnly, HospitalConfigurationPermission
from apps.identity.models import Invitation, StaffProfile, UserRole

from .base import HospitalConfigurationViewSet


class HospitalProfileView(APIView):
    permission_classes = [HospitalConfigurationPermission]

    def get(self, request):
        profile = HospitalProfile.objects.first()
        return Response({"data": HospitalProfileSerializer(profile).data if profile else None})

    def put(self, request):
        self._require_head_of_service(request)
        profile = HospitalProfile.objects.first()
        before = HospitalProfileSerializer(profile).data if profile else {}
        serializer = HospitalProfileSerializer(instance=profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        saved = serializer.save(singleton_key=1)
        record_audit_event(
            actor=request.user,
            request=request,
            action="hospital.hospitalprofile.configured",
            object_type="hospital.HospitalProfile",
            object_id=saved.id,
            before=dict(before),
            after=dict(HospitalProfileSerializer(saved).data),
        )
        return Response(
            {"data": HospitalProfileSerializer(saved).data},
            status=status.HTTP_200_OK if profile else status.HTTP_201_CREATED,
        )

    def patch(self, request):
        self._require_head_of_service(request)
        profile = HospitalProfile.objects.first()
        if not profile:
            return Response(
                {"detail": "Configure the hospital profile before applying partial updates."},
                status=status.HTTP_404_NOT_FOUND,
            )
        before = dict(HospitalProfileSerializer(profile).data)
        serializer = HospitalProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        saved = serializer.save(singleton_key=1)
        record_audit_event(
            actor=request.user,
            request=request,
            action="hospital.hospitalprofile.updated",
            object_type="hospital.HospitalProfile",
            object_id=saved.id,
            before=before,
            after=dict(HospitalProfileSerializer(saved).data),
        )
        return Response({"data": HospitalProfileSerializer(saved).data})

    @staticmethod
    def _require_head_of_service(request) -> None:
        permission = HeadOfServiceOnly()
        if not permission.has_permission(request, None):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(permission.message)


class HeadOfServiceDashboardView(APIView):
    permission_classes = [HeadOfServiceOnly]

    def get(self, request):
        now = timezone.now()
        active_clinical_staff = StaffProfile.objects.filter(
            user__is_active=True,
            user__role__in=[UserRole.DOCTOR, UserRole.NURSE],
            employment_status="ACTIVE",
        ).count()
        pending_invitations = Invitation.objects.filter(
            accepted_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=now,
            intended_role__in=[UserRole.DOCTOR, UserRole.NURSE],
        ).count()
        external_hospitals = ExternalHospital.objects.filter(is_active=True)
        incomplete_external = (
            external_hospitals.filter(
                Q(transfer_email="")
                | (Q(specialty_capabilities__isnull=True) & Q(service_capabilities__isnull=True))
            )
            .distinct()
            .count()
        )

        return Response(
            {
                "staff": {
                    "active_clinical": active_clinical_staff,
                    "pending_invitations": pending_invitations,
                },
                "operations": {
                    "departments": Department.objects.filter(is_active=True).count(),
                    "available_beds": Bed.objects.filter(status=Bed.Status.AVAILABLE).count(),
                    "total_beds": Bed.objects.count(),
                    "resources_unavailable": Resource.objects.filter(
                        status__in=[Resource.Status.UNAVAILABLE, Resource.Status.MAINTENANCE]
                    ).count(),
                },
                "transfers": {
                    "external_hospitals": external_hospitals.count(),
                    "incomplete_profiles": incomplete_external,
                },
                "hospital_profile_configured": HospitalProfile.objects.exists(),
                "generated_at": now,
            }
        )


class DepartmentViewSet(HospitalConfigurationViewSet):
    serializer_class = DepartmentSerializer
    search_fields = ["code", "name", "location"]
    ordering_fields = ["code", "name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = Department.objects.select_related("parent", "head__user").annotate(
            staff_count=Count("staff_members", distinct=True)
        )
        active = self.request.query_params.get("is_active")
        if active in {"true", "false"}:
            queryset = queryset.filter(is_active=active == "true")
        return queryset
