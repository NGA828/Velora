from rest_framework.exceptions import MethodNotAllowed
from rest_framework.viewsets import ModelViewSet

from apps.audit.services import record_audit_event


class AuditedNoDestroyModelViewSet(ModelViewSet):
    """CRUD without hard delete, with transport-safe create/update audit snapshots."""

    def perform_create(self, serializer):
        instance = serializer.save()
        record_audit_event(
            actor=self.request.user,
            request=self.request,
            action=f"{instance._meta.label_lower}.created",
            object_type=instance._meta.label,
            object_id=instance.pk,
            after=dict(self.get_serializer(instance).data),
        )

    def perform_update(self, serializer):
        instance = serializer.instance
        before = dict(self.get_serializer(instance).data)
        updated = serializer.save()
        record_audit_event(
            actor=self.request.user,
            request=self.request,
            action=f"{updated._meta.label_lower}.updated",
            object_type=updated._meta.label,
            object_id=updated.pk,
            before=before,
            after=dict(self.get_serializer(updated).data),
        )

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed("DELETE", detail="Archive or deactivate this record instead.")
