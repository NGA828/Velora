from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "recipient", "category", "severity", "title", "read_at")
    list_filter = ("category", "severity")
    search_fields = ("recipient__email", "title", "patient__medical_record_number")
    readonly_fields = [field.name for field in Notification._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
