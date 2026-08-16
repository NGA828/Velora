from django.contrib import admin

from apps.calls.models import CallParticipant, CallSession, CallWebhookEvent


class CallParticipantInline(admin.TabularInline):
    model = CallParticipant
    extra = 0
    readonly_fields = ("user", "provider_identity", "status", "joined_at", "left_at")


@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "initiated_by", "status", "initiated_at", "answered_at", "ended_at")
    list_filter = ("status", "direction")
    search_fields = ("provider_sid", "initiated_by__email")
    inlines = (CallParticipantInline,)


@admin.register(CallWebhookEvent)
class CallWebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "provider_event_id",
        "event_type",
        "call_session",
        "received_at",
        "processed_at",
    )
    readonly_fields = [field.name for field in CallWebhookEvent._meta.fields]
