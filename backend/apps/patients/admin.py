from django.contrib import admin

from apps.patients.models import CareEpisode, GuardianAccess, Patient, PatientCareAssignment


class CareAssignmentInline(admin.TabularInline):
    model = PatientCareAssignment
    extra = 0
    readonly_fields = ("starts_at", "ends_at", "assigned_by")


class GuardianAccessInline(admin.TabularInline):
    model = GuardianAccess
    extra = 0
    readonly_fields = ("invitation", "guardian", "status", "granted_at", "revoked_at")


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "medical_record_number",
        "last_name",
        "first_name",
        "date_of_birth",
        "status",
        "created_at",
    )
    list_filter = ("status", "sex_at_birth")
    search_fields = ("medical_record_number", "first_name", "last_name")
    inlines = (CareAssignmentInline, GuardianAccessInline)


@admin.register(CareEpisode)
class CareEpisodeAdmin(admin.ModelAdmin):
    list_display = ("episode_number", "patient", "episode_type", "department", "status")
    list_filter = ("episode_type", "status", "department")
    search_fields = ("episode_number", "patient__medical_record_number")


@admin.register(PatientCareAssignment)
class PatientCareAssignmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "staff", "assignment_type", "is_primary", "starts_at", "ends_at")
    list_filter = ("assignment_type", "is_primary")


@admin.register(GuardianAccess)
class GuardianAccessAdmin(admin.ModelAdmin):
    list_display = ("patient", "relationship", "guardian", "status", "created_at")
    list_filter = ("status",)
