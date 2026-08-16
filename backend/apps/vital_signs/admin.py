from django.contrib import admin

from apps.vital_signs.models import (
    VitalMetric,
    VitalObservation,
    VitalRule,
    VitalRuleEvaluation,
    VitalRuleSet,
    VitalValue,
)


@admin.register(VitalMetric)
class VitalMetricAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "unit", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


class VitalRuleInline(admin.TabularInline):
    model = VitalRule
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(VitalRuleSet)
class VitalRuleSetAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "status", "effective_from", "approved_by")
    list_filter = ("status",)
    inlines = (VitalRuleInline,)
    readonly_fields = (
        "status",
        "active_marker",
        "effective_from",
        "effective_to",
        "approved_by",
        "approved_at",
    )


@admin.register(VitalRule)
class VitalRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "rule_set", "metric", "operator", "priority", "is_active")
    list_filter = ("operator", "is_active")
    search_fields = ("name", "metric__name")


class VitalValueInline(admin.TabularInline):
    model = VitalValue
    extra = 0
    readonly_fields = ("metric", "value")


@admin.register(VitalObservation)
class VitalObservationAdmin(admin.ModelAdmin):
    list_display = ("patient", "observed_at", "status", "recorded_by", "rule_set")
    list_filter = ("status", "rule_set")
    search_fields = ("patient__medical_record_number", "patient__first_name", "patient__last_name")
    readonly_fields = ("status", "analyzed_at", "rule_set")
    inlines = (VitalValueInline,)


@admin.register(VitalRuleEvaluation)
class VitalRuleEvaluationAdmin(admin.ModelAdmin):
    list_display = (
        "observation",
        "metric_name_snapshot",
        "rule_name_snapshot",
        "measured_value",
        "matched",
    )
    list_filter = ("matched",)
    readonly_fields = [field.name for field in VitalRuleEvaluation._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
