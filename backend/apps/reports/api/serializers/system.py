from rest_framework import serializers

from apps.audit.models import AuditEvent
from apps.identity.models import User


class SystemUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    employee_number = serializers.CharField(
        source="staff_profile.employee_number", read_only=True, default=None
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "role",
            "role_label",
            "employee_number",
            "is_active",
            "must_change_password",
            "last_login",
            "date_joined",
        )
        read_only_fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "role",
            "role_label",
            "employee_number",
            "last_login",
            "date_joined",
        )


class SystemUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("is_active", "must_change_password")


class RedactedAuditEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True, default=None)
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "created_at",
            "actor_name",
            "actor_email",
            "action",
            "object_type",
            "object_id",
            "reason",
            "request_id",
            "ip_address",
        )
