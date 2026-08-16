from rest_framework import serializers

from apps.calls.models import CallParticipant, CallSession


class CallParticipantSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = CallParticipant
        fields = (
            "id",
            "user_id",
            "full_name",
            "role",
            "provider_identity",
            "status",
            "joined_at",
            "left_at",
        )


class CallSessionSerializer(serializers.ModelSerializer):
    initiated_by_name = serializers.CharField(source="initiated_by.get_full_name", read_only=True)
    patient_name = serializers.CharField(
        source="patient.get_full_name", read_only=True, default=None
    )
    participants = CallParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = CallSession
        fields = "__all__"


class CallCreateSerializer(serializers.Serializer):
    recipient = serializers.UUIDField()
    conversation = serializers.UUIDField(required=False, allow_null=True)
