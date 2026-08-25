from django.contrib import admin

from .models import AssistantAuditLog, AssistantMessage, AssistantSession


@admin.register(AssistantSession)
class AssistantSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "patient", "title", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("user__email", "patient__first_name", "patient__last_name", "patient__medical_record_number")


@admin.register(AssistantMessage)
class AssistantMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "role", "validation_passed", "created_at")
    list_filter = ("role", "validation_passed", "created_at")
    search_fields = ("content",)


@admin.register(AssistantAuditLog)
class AssistantAuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "patient", "action", "status", "recommendation_id", "created_at")
    list_filter = ("action", "status", "created_at")
    search_fields = ("user__email", "patient__medical_record_number", "question", "recommendation_id")
