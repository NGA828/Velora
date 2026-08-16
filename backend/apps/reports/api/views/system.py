from datetime import timedelta

from django.conf import settings
from django.db import connection
from django.db.models import Count
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.audit.models import AuditEvent, SystemHeartbeat
from apps.audit.services import record_audit_event
from apps.calls.models import CallWebhookEvent
from apps.identity.models import LoginEvent, LoginOutcome, User
from apps.reports.api.serializers import (
    RedactedAuditEventSerializer,
    SystemUserSerializer,
    SystemUserUpdateSerializer,
)
from apps.reports.permissions import AdminOnly
from apps.transfers.models import TransferTransmission
from integrations.twilio.config import get_twilio_settings


class SystemDashboardView(APIView):
    permission_classes = [AdminOnly]

    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            database_ok = cursor.fetchone()[0] == 1
        heartbeat = SystemHeartbeat.objects.filter(service="medication-reminder-worker").first()
        heartbeat_ok = bool(
            heartbeat and heartbeat.last_seen_at >= timezone.now() - timedelta(seconds=90)
        )
        return Response(
            {
                "database": {"healthy": database_ok, "engine": "SQLite"},
                "scheduler": {
                    "healthy": heartbeat_ok,
                    "last_seen_at": heartbeat.last_seen_at if heartbeat else None,
                },
                "integrations": {
                    "twilio_configured": get_twilio_settings().available,
                    "smtp_configured": bool(settings.EMAIL_HOST),
                },
                "users": {
                    "active": User.objects.filter(is_active=True).count(),
                    "inactive": User.objects.filter(is_active=False).count(),
                    "by_role": list(
                        User.objects.values("role").annotate(count=Count("id")).order_by("role")
                    ),
                },
                "security": {
                    "failed_logins_24h": LoginEvent.objects.filter(
                        occurred_at__gte=timezone.now() - timedelta(hours=24),
                        outcome__in=[
                            LoginOutcome.INVALID_CREDENTIALS,
                            LoginOutcome.INACTIVE_ACCOUNT,
                        ],
                    ).count(),
                    "audit_events_24h": AuditEvent.objects.filter(
                        created_at__gte=timezone.now() - timedelta(hours=24)
                    ).count(),
                },
                "failures": {
                    "transfer_email": TransferTransmission.objects.filter(status="FAILED").count(),
                    "twilio_webhooks": CallWebhookEvent.objects.exclude(
                        processing_error=""
                    ).count(),
                },
            }
        )


class SystemUserViewSet(ReadOnlyModelViewSet):
    permission_classes = [AdminOnly]
    queryset = User.objects.select_related("staff_profile").all()

    def get_serializer_class(self):
        return (
            SystemUserUpdateSerializer
            if self.action in {"update", "partial_update"}
            else SystemUserSerializer
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        user = self.get_object()
        if user == request.user and request.data.get("is_active") is False:
            raise serializers.ValidationError("You cannot deactivate your own account.")
        before = {
            "is_active": user.is_active,
            "must_change_password": user.must_change_password,
        }
        serializer = SystemUserUpdateSerializer(user, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_audit_event(
            actor=request.user,
            request=request,
            action="identity.user.system_updated",
            object_type="identity.User",
            object_id=user.id,
            before=before,
            after={
                "is_active": user.is_active,
                "must_change_password": user.must_change_password,
            },
        )
        return Response(SystemUserSerializer(user).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class RedactedAuditEventViewSet(ReadOnlyModelViewSet):
    permission_classes = [AdminOnly]
    serializer_class = RedactedAuditEventSerializer

    def get_queryset(self):
        queryset = AuditEvent.objects.select_related("actor")
        action = self.request.query_params.get("action")
        if action:
            queryset = queryset.filter(action__icontains=action)
        return queryset
