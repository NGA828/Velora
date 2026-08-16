from django.contrib import admin

from apps.prescriptions.models import (
    DoseScheduleRule,
    Medication,
    MedicationDose,
    MedicationDoseEvent,
    Prescription,
    PrescriptionItem,
)


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ("generic_name", "brand_name", "strength", "form", "is_active")
    list_filter = ("is_active", "form")
    search_fields = ("generic_name", "brand_name", "strength")


class ScheduleRuleInline(admin.TabularInline):
    model = DoseScheduleRule
    extra = 0


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0
    show_change_link = True


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("patient", "prescribed_by", "status", "starts_on", "ends_on")
    list_filter = ("status",)
    search_fields = ("patient__medical_record_number", "patient__first_name", "patient__last_name")
    readonly_fields = ("activated_at", "completed_at", "cancelled_at")
    inlines = (PrescriptionItemInline,)


@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(admin.ModelAdmin):
    list_display = ("prescription", "medication", "dose_amount", "dose_unit", "route")
    inlines = (ScheduleRuleInline,)


class MedicationDoseEventInline(admin.TabularInline):
    model = MedicationDoseEvent
    extra = 0
    readonly_fields = (
        "actor",
        "previous_status",
        "new_status",
        "occurred_at",
        "notes",
    )


@admin.register(MedicationDose)
class MedicationDoseAdmin(admin.ModelAdmin):
    list_display = ("prescription_item", "scheduled_for", "status", "actual_at", "acted_by")
    list_filter = ("status",)
    search_fields = (
        "prescription_item__prescription__patient__medical_record_number",
        "prescription_item__medication__generic_name",
    )
    readonly_fields = ("scheduled_for", "actual_at", "acted_by", "due_notification_sent_at")
    inlines = (MedicationDoseEventInline,)


@admin.register(MedicationDoseEvent)
class MedicationDoseEventAdmin(admin.ModelAdmin):
    list_display = ("dose", "previous_status", "new_status", "actor", "occurred_at")
    list_filter = ("new_status",)
    readonly_fields = [field.name for field in MedicationDoseEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
