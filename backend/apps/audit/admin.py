from django.contrib import admin

from apps.audit.models import AuditEvent, MedicalRecordAccess, SystemHeartbeat


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "object_type", "object_id", "actor")
    list_filter = ("action", "object_type")
    search_fields = ("object_id", "request_id", "actor__email")
    readonly_fields = [field.name for field in AuditEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MedicalRecordAccess)
class MedicalRecordAccessAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "patient", "object_type", "action")
    list_filter = ("action", "object_type")
    search_fields = ("user__email", "patient__medical_record_number", "request_id")
    readonly_fields = [field.name for field in MedicalRecordAccess._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SystemHeartbeat)
class SystemHeartbeatAdmin(admin.ModelAdmin):
    list_display = ("service", "status", "last_seen_at", "updated_at")
    readonly_fields = ("service", "status", "last_seen_at", "details")
