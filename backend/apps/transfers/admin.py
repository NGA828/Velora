from django.contrib import admin

from apps.transfers.models import (
    TransferDecision,
    TransferRecommendation,
    TransferRequest,
    TransferRequirement,
    TransferStatusEvent,
    TransferTransmission,
)


class RequirementInline(admin.TabularInline):
    model = TransferRequirement
    extra = 0


@admin.register(TransferRequest)
class TransferRequestAdmin(admin.ModelAdmin):
    list_display = ("patient", "requested_by", "urgency", "status", "selected_hospital")
    list_filter = ("status", "urgency")
    search_fields = ("patient__medical_record_number", "patient__first_name", "patient__last_name")
    inlines = (RequirementInline,)


@admin.register(TransferRecommendation)
class TransferRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "transfer_request",
        "external_hospital",
        "generation",
        "eligible",
        "score",
        "rank",
    )
    list_filter = ("eligible", "generation")


@admin.register(TransferDecision)
class TransferDecisionAdmin(admin.ModelAdmin):
    list_display = ("transfer_request", "guardian", "decision", "decided_at")
    list_filter = ("decision",)


@admin.register(TransferStatusEvent)
class TransferStatusEventAdmin(admin.ModelAdmin):
    list_display = ("transfer_request", "previous_status", "new_status", "actor", "occurred_at")
    readonly_fields = [field.name for field in TransferStatusEvent._meta.fields]


@admin.register(TransferTransmission)
class TransferTransmissionAdmin(admin.ModelAdmin):
    list_display = ("transfer_request", "external_hospital", "status", "attempts", "sent_at")
    list_filter = ("status",)
    readonly_fields = ("checksum", "package_storage_key", "attempts", "last_error", "sent_at")
