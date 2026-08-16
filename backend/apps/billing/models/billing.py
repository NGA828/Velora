from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class ChargeItem(UUIDTimeStampedModel):
    class Category(models.TextChoices):
        SERVICE = "SERVICE", "Service"
        ROOM = "ROOM", "Room"
        MEDICATION = "MEDICATION", "Medication"
        PROCEDURE = "PROCEDURE", "Procedure"
        OTHER = "OTHER", "Other"

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=16, choices=Category.choices)
    default_unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["category", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(default_unit_price__gte=Decimal("0")),
                name="charge_item_price_nonnegative",
            )
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Invoice(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ISSUED = "ISSUED", "Issued"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially paid"
        PAID = "PAID", "Paid"
        VOID = "VOID", "Void"

    invoice_number = models.CharField(max_length=48, unique=True)
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    care_episode = models.ForeignKey(
        "patients.CareEpisode",
        on_delete=models.PROTECT,
        related_name="invoices",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    currency = models.CharField(
        max_length=3,
        default="XAF",
        help_text="ISO 4217 currency snapshot for this invoice.",
    )
    issued_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    adjustments = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invoices_created",
    )
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invoices_voided",
        null=True,
        blank=True,
    )
    void_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-issued_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(subtotal__gte=Decimal("0")),
                name="invoice_subtotal_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(total__gte=Decimal("0")),
                name="invoice_total_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(amount_paid__gte=Decimal("0")),
                name="invoice_amount_paid_nonnegative",
            ),
        ]

    @property
    def outstanding_amount(self):
        return self.total - self.amount_paid

    def __str__(self) -> str:
        return self.invoice_number


class InvoiceLine(UUIDTimeStampedModel):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name="lines",
    )
    charge_item = models.ForeignKey(
        ChargeItem,
        on_delete=models.PROTECT,
        related_name="invoice_lines",
        null=True,
        blank=True,
    )
    description = models.CharField(max_length=240)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)
    service_date = models.DateField()

    class Meta:
        ordering = ["service_date", "created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=Decimal("0")),
                name="invoice_line_quantity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=Decimal("0")),
                name="invoice_line_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(line_total__gte=Decimal("0")),
                name="invoice_line_total_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        return self.description


class Payment(UUIDTimeStampedModel):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        CARD = "CARD", "Card"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank transfer"
        MOBILE_MONEY = "MOBILE_MONEY", "Mobile money"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        POSTED = "POSTED", "Posted"
        REVERSED = "REVERSED", "Reversed"

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    receipt_number = models.CharField(max_length=48, unique=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices)
    reference = models.CharField(max_length=120, blank=True)
    received_at = models.DateTimeField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments_recorded",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.POSTED,
        db_index=True,
    )
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments_reversed",
        null=True,
        blank=True,
    )
    reversal_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-received_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0")),
                name="payment_amount_positive",
            )
        ]

    def __str__(self) -> str:
        return self.receipt_number
