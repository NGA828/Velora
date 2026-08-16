from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True, default=None)
    patient_name = serializers.CharField(
        source="patient.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = Notification
        fields = (
            "id",
            "category",
            "severity",
            "title",
            "body",
            "route",
            "data",
            "actor_name",
            "patient",
            "patient_name",
            "delivered_at",
            "read_at",
            "created_at",
        )
