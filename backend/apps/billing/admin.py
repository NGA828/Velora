from django.contrib import admin

from apps.billing.models import ChargeItem, Invoice, InvoiceLine, Payment


@admin.register(ChargeItem)
class ChargeItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "default_unit_price", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("code", "name")


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = ("line_total",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "patient",
        "status",
        "total",
        "amount_paid",
        "issued_at",
    )
    list_filter = ("status",)
    search_fields = ("invoice_number", "patient__medical_record_number")
    readonly_fields = ("subtotal", "total", "amount_paid", "issued_at", "voided_at")
    inlines = (InvoiceLineInline,)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "invoice", "amount", "method", "status", "received_at")
    list_filter = ("status", "method")
    search_fields = ("receipt_number", "invoice__invoice_number", "reference")
    readonly_fields = ("receipt_number", "reversed_at", "reversed_by")
