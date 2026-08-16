from django.contrib import admin

from apps.clinical_records.models import (
    Allergy,
    ClinicalNote,
    Diagnosis,
    MedicalFile,
    MedicalHistoryEntry,
    TreatmentPlan,
)


@admin.register(MedicalFile)
class MedicalFileAdmin(admin.ModelAdmin):
    list_display = ("file_number", "patient", "status", "opened_at", "opened_by")
    list_filter = ("status",)
    search_fields = ("file_number", "patient__medical_record_number")
    readonly_fields = ("file_number", "patient", "opened_at", "opened_by")


@admin.register(Allergy)
class AllergyAdmin(admin.ModelAdmin):
    list_display = ("patient", "substance", "severity", "status", "recorded_at")
    list_filter = ("severity", "status", "guardian_visibility")
    search_fields = ("patient__medical_record_number", "substance")


@admin.register(MedicalHistoryEntry)
class MedicalHistoryEntryAdmin(admin.ModelAdmin):
    list_display = ("patient", "title", "category", "occurred_on", "recorded_by")
    list_filter = ("category", "guardian_visibility")
    search_fields = ("patient__medical_record_number", "title")


@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ("patient", "name_snapshot", "status", "diagnosed_at", "diagnosed_by")
    list_filter = ("status", "guardian_visibility")
    search_fields = ("patient__medical_record_number", "name_snapshot", "code_snapshot")


@admin.register(TreatmentPlan)
class TreatmentPlanAdmin(admin.ModelAdmin):
    list_display = ("patient", "title", "status", "starts_on", "ends_on", "authored_by")
    list_filter = ("status", "guardian_visibility")
    search_fields = ("patient__medical_record_number", "title")


@admin.register(ClinicalNote)
class ClinicalNoteAdmin(admin.ModelAdmin):
    list_display = ("patient", "title", "note_type", "status", "author", "signed_at")
    list_filter = ("note_type", "status", "guardian_visibility")
    search_fields = ("patient__medical_record_number", "title", "author__email")
    readonly_fields = ("signed_at",)
