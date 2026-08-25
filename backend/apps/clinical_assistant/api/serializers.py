from rest_framework import serializers

from apps.clinical_assistant.models import AssistantMessage, AssistantSession


class AssistantMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantMessage
        fields = [
            "id",
            "role",
            "content",
            "validation_passed",
            "created_at",
        ]
        read_only_fields = fields


class AssistantSessionSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    messages = AssistantMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AssistantSession
        fields = [
            "id",
            "patient",
            "patient_name",
            "title",
            "is_active",
            "created_at",
            "updated_at",
            "messages",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "patient_name", "messages"]

    def get_patient_name(self, obj) -> str:
        return obj.patient.get_full_name() if obj.patient else ""


class ChatRequestSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField(required=True)
    message = serializers.CharField(required=True, min_length=1, max_length=4000)
    session_id = serializers.UUIDField(required=False, allow_null=True)


class ChatResponseSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    message = AssistantMessageSerializer()
    fallback = serializers.BooleanField()
    context_summary = serializers.DictField()
