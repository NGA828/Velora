from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_audit_event
from apps.identity.api.serializers import (
    InvitationSerializer,
    StaffInvitationCreateSerializer,
    StaffProfileSerializer,
    StaffProfileUpdateSerializer,
)
from apps.identity.models import EmploymentStatus, Invitation, StaffProfile, UserRole
from apps.identity.permissions import CanManageStaff, CanViewClinicalStaffDirectory
from apps.identity.selectors import staff_visible_to
from apps.identity.services import create_invitation, revoke_invitation


def _validation_error(exc: DjangoValidationError) -> serializers.ValidationError:
    if hasattr(exc, "message_dict"):
        return serializers.ValidationError(exc.message_dict)
    return serializers.ValidationError({"detail": exc.messages})


def _invitations_visible_to(user):
    queryset = Invitation.objects.select_related("invited_by")
    if user.role == UserRole.ADMIN:
        return queryset
    return queryset.filter(intended_role__in=[UserRole.DOCTOR, UserRole.NURSE])


class StaffListView(generics.ListAPIView):
    permission_classes = [CanManageStaff]
    serializer_class = StaffProfileSerializer
    search_fields = ("user__first_name", "user__last_name", "user__email", "employee_number")

    def get_queryset(self):
        return staff_visible_to(self.request.user)


class ClinicalStaffDirectoryView(generics.ListAPIView):
    permission_classes = [CanViewClinicalStaffDirectory]
    serializer_class = StaffProfileSerializer

    def get_queryset(self):
        queryset = StaffProfile.objects.filter(
            user__is_active=True,
            employment_status=EmploymentStatus.ACTIVE,
            user__role__in=[UserRole.DOCTOR, UserRole.NURSE],
        ).select_related("user", "department")
        role = self.request.query_params.get("role")
        if role in {UserRole.DOCTOR, UserRole.NURSE}:
            queryset = queryset.filter(user__role=role)
        return queryset


class StaffDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [CanManageStaff]

    def get_queryset(self):
        return staff_visible_to(self.request.user)

    def get_serializer_class(self):
        if self.request.method in {"PUT", "PATCH"}:
            return StaffProfileUpdateSerializer
        return StaffProfileSerializer

    def perform_update(self, serializer):
        instance = serializer.instance
        before = dict(StaffProfileSerializer(instance).data)
        updated = serializer.save()
        record_audit_event(
            actor=self.request.user,
            request=self.request,
            action="identity.staffprofile.updated",
            object_type="identity.StaffProfile",
            object_id=updated.id,
            before=before,
            after=dict(StaffProfileSerializer(updated).data),
        )


class StaffInvitationListCreateView(generics.GenericAPIView):
    permission_classes = [CanManageStaff]

    def get(self, request):
        queryset = _invitations_visible_to(request.user)
        page = self.paginate_queryset(queryset)
        serializer = InvitationSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = StaffInvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            invitation, _ = create_invitation(
                inviter=request.user,
                email=data["email"],
                intended_role=data["intended_role"],
                context=serializer.invitation_context(),
                request=request,
            )
        except DjangoValidationError as exc:
            raise _validation_error(exc) from exc
        return Response(
            InvitationSerializer(invitation).data,
            status=status.HTTP_201_CREATED,
        )


class InvitationRevokeView(APIView):
    permission_classes = [CanManageStaff]

    def post(self, request, invitation_id):
        invitation = generics.get_object_or_404(
            _invitations_visible_to(request.user), pk=invitation_id
        )
        try:
            revoked = revoke_invitation(
                invitation=invitation,
                actor=request.user,
                request=request,
            )
        except DjangoValidationError as exc:
            raise _validation_error(exc) from exc
        return Response(InvitationSerializer(revoked).data)
