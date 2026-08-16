from django.contrib import admin

from apps.monitoring.models import MonitoringQuestion, MonitoringResponse, MonitoringThread


class MonitoringQuestionInline(admin.TabularInline):
    model = MonitoringQuestion
    extra = 0


@admin.register(MonitoringThread)
class MonitoringThreadAdmin(admin.ModelAdmin):
    list_display = ("patient", "subject", "doctor", "guardian", "status", "opened_at")
    list_filter = ("status",)
    search_fields = ("patient__medical_record_number", "subject")
    inlines = (MonitoringQuestionInline,)


@admin.register(MonitoringQuestion)
class MonitoringQuestionAdmin(admin.ModelAdmin):
    list_display = ("thread", "sequence", "response_type", "asked_at", "due_at")
    list_filter = ("response_type",)


@admin.register(MonitoringResponse)
class MonitoringResponseAdmin(admin.ModelAdmin):
    list_display = ("question", "guardian", "submitted_at", "is_current")
    list_filter = ("is_current",)
    readonly_fields = ("answer", "submitted_at", "supersedes")
