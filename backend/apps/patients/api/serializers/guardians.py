from rest_framework import serializers

from apps.patients.models import GuardianAccess


class GuardianAccessSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    guardian_profile = serializers.UUIDField(
        source="guardian.id", read_only=True, allow_null=True, default=None
    )
    invited_at = serializers.DateTimeField(source="invitation.created_at", read_only=True)
    accepted_at = serializers.DateTimeField(source="invitation.accepted_at", read_only=True)

    class Meta:
        model = GuardianAccess
        fields = (
            "id",
            "patient",
            "guardian_profile",
            "email",
            "full_name",
            "relationship",
            "status",
            "can_view_medical_file",
            "can_answer_monitoring",
            "can_decide_transfers",
            "can_view_billing",
            "invited_at",
            "accepted_at",
            "granted_at",
            "revoked_at",
        )

    def get_email(self, access) -> str:
        return access.guardian.user.email if access.guardian else access.invitation.email

    def get_full_name(self, access) -> str:
        return access.guardian.user.get_full_name() if access.guardian else "Invitation pending"


class GuardianInvitationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    relationship = serializers.CharField(max_length=80)
    can_view_medical_file = serializers.BooleanField(default=True)
    can_answer_monitoring = serializers.BooleanField(default=True)
    can_decide_transfers = serializers.BooleanField(default=True)
    can_view_billing = serializers.BooleanField(default=False)
