from rest_framework import serializers

from apps.messaging.models import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
)


class EligibleContactSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField(source="get_full_name")
    email = serializers.EmailField()
    role = serializers.CharField()
    role_label = serializers.CharField(source="get_role_display")


class ConversationParticipantSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    role_label = serializers.CharField(source="user.get_role_display", read_only=True)

    class Meta:
        model = ConversationParticipant
        fields = (
            "id",
            "user_id",
            "full_name",
            "role",
            "role_label",
            "joined_at",
            "left_at",
            "is_muted",
        )


class MessageAttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = MessageAttachment
        fields = (
            "id",
            "original_name",
            "mime_type",
            "byte_size",
            "checksum",
            "download_url",
        )

    def get_download_url(self, attachment):
        return (
            f"/api/v1/conversations/{attachment.message.conversation_id}/"
            f"attachments/{attachment.id}/download/"
        )


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    sender_role = serializers.CharField(source="sender.role", read_only=True)
    attachment = MessageAttachmentSerializer(read_only=True)
    delivery_state = serializers.SerializerMethodField()
    own_receipt = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "id",
            "conversation",
            "sender",
            "sender_name",
            "sender_role",
            "message_type",
            "body",
            "client_message_id",
            "reply_to",
            "sent_at",
            "attachment",
            "delivery_state",
            "own_receipt",
        )

    def get_delivery_state(self, message):
        receipts = list(message.receipts.all())
        if not receipts:
            return "SENT"
        if all(receipt.seen_at for receipt in receipts):
            return "SEEN"
        if all(receipt.delivered_at for receipt in receipts):
            return "DELIVERED"
        return "SENT"

    def get_own_receipt(self, message):
        request = self.context.get("request")
        if not request:
            return None
        receipt = next(
            (item for item in message.receipts.all() if item.recipient_id == request.user.id),
            None,
        )
        return (
            {
                "delivered_at": receipt.delivered_at,
                "seen_at": receipt.seen_at,
            }
            if receipt
            else None
        )


class ConversationSerializer(serializers.ModelSerializer):
    participants = ConversationParticipantSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(
        source="patient.get_full_name", read_only=True, default=None
    )
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = "__all__"

    def get_last_message(self, conversation):
        message = conversation.messages.order_by("-sent_at").first()
        return MessageSerializer(message, context=self.context).data if message else None

    def get_unread_count(self, conversation):
        request = self.context.get("request")
        if not request:
            return 0
        return conversation.messages.filter(
            receipts__recipient=request.user,
            receipts__seen_at__isnull=True,
        ).count()


class ConversationCreateSerializer(serializers.Serializer):
    participant = serializers.UUIDField()
    patient = serializers.UUIDField(required=False, allow_null=True)
    subject = serializers.CharField(max_length=180, required=False, allow_blank=True, default="")


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(required=False, allow_blank=True, default="")
    client_message_id = serializers.CharField(max_length=64)


class ReceiptAcknowledgeSerializer(serializers.Serializer):
    up_to_message = serializers.UUIDField()
