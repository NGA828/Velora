from django.contrib import admin

from apps.death_certificates.models import DeathCertificate


@admin.register(DeathCertificate)
class DeathCertificateAdmin(admin.ModelAdmin):
    list_display = (
        "certificate_number",
        "patient",
        "death_datetime",
        "issuing_doctor",
        "status",
        "issued_at",
    )
    list_filter = ("status", "manner_of_death")
    search_fields = ("certificate_number", "patient__medical_record_number")
    readonly_fields = (
        "certificate_number",
        "issuing_doctor",
        "issued_at",
        "voided_at",
        "voided_by",
    )
