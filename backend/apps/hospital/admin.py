from django.contrib import admin

from apps.hospital.models import (
    Bed,
    ClinicalCondition,
    Department,
    ExternalHospital,
    ExternalHospitalService,
    ExternalHospitalSpecialty,
    ExternalSpecialist,
    HospitalProfile,
    HospitalServiceAvailability,
    Resource,
    Room,
    ServiceDefinition,
    Specialty,
    SpecialtyCondition,
)


@admin.register(HospitalProfile)
class HospitalProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "city", "country", "updated_at")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(Specialty, ClinicalCondition, ServiceDefinition)
class CatalogAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(SpecialtyCondition)
class SpecialtyConditionAdmin(admin.ModelAdmin):
    list_display = ("specialty", "condition", "match_weight")
    list_select_related = ("specialty", "condition")


@admin.register(HospitalServiceAvailability)
class HospitalServiceAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("service", "department", "availability_status")
    list_filter = ("availability_status", "department")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("code", "department", "room_type", "status")
    list_filter = ("status", "department")


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ("code", "room", "status")
    list_filter = ("status",)


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = (
        "asset_code",
        "name",
        "department",
        "quantity_available",
        "quantity_total",
        "status",
    )
    list_filter = ("status", "category", "department")
    search_fields = ("asset_code", "name")


@admin.register(ExternalHospital)
class ExternalHospitalAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "phone", "transfer_email", "is_active")
    list_filter = ("is_active", "country")
    search_fields = ("name", "city", "transfer_email")


@admin.register(ExternalHospitalSpecialty, ExternalHospitalService)
class ExternalCapabilityAdmin(admin.ModelAdmin):
    list_display = ("external_hospital", "availability_status", "updated_at")
    list_filter = ("availability_status",)


@admin.register(ExternalSpecialist)
class ExternalSpecialistAdmin(admin.ModelAdmin):
    list_display = ("full_name", "external_hospital", "specialty", "is_active")
    list_filter = ("is_active", "specialty")
    search_fields = ("full_name", "external_hospital__name")
