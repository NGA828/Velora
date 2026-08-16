from django.contrib import admin

from apps.messaging.models import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
    MessageReceipt,
)


class ParticipantInline(admin.TabularInline):
    model = ConversationParticipant
    extra = 0
    readonly_fields = ("user", "joined_at", "left_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation_type", "subject", "patient", "created_by", "is_active")
    list_filter = ("conversation_type", "is_active")
    inlines = (ParticipantInline,)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "message_type", "sent_at")
    list_filter = ("message_type",)
    search_fields = ("sender__email", "body")
    readonly_fields = ("conversation", "sender", "body", "sent_at", "client_message_id")


@admin.register(MessageReceipt)
class MessageReceiptAdmin(admin.ModelAdmin):
    list_display = ("message", "recipient", "delivered_at", "seen_at")
    readonly_fields = [field.name for field in MessageReceipt._meta.fields]


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "message", "mime_type", "byte_size", "checksum")
    readonly_fields = [field.name for field in MessageAttachment._meta.fields]
