from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.notifications.api.serializers import NotificationSerializer
from apps.notifications.models import Notification


class NotificationViewSet(ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        queryset = Notification.objects.filter(
            recipient=self.request.user,
            archived_at__isnull=True,
        ).select_related("actor", "patient")
        unread = self.request.query_params.get("unread")
        return queryset.filter(read_at__isnull=True) if unread == "true" else queryset

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = self.get_object()
        if not notification.read_at:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at", "updated_at"])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        updated = self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({"updated": updated})
