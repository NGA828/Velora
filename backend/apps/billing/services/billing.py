import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.billing.models import Invoice, InvoiceLine, Payment
from apps.hospital.models import HospitalProfile
from apps.identity.models import UserRole
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.patients.models import GuardianAccess


def _require_accounting(user):
    if user.role != UserRole.ACCOUNTING or not user.is_active:
        raise ValidationError("Only active Accounting personnel may perform this action.")


def _number(prefix):
    return f"{prefix}-{timezone.localdate():%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"


def _recalculate(invoice):
    subtotal = invoice.lines.aggregate(total=Sum("line_total"))["total"] or Decimal("0")
    amount_paid = invoice.payments.filter(status=Payment.Status.POSTED).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")
    total = max(Decimal("0"), subtotal + invoice.adjustments)
    invoice.subtotal = subtotal
    invoice.total = total
    invoice.amount_paid = amount_paid
    if invoice.status not in {Invoice.Status.DRAFT, Invoice.Status.VOID}:
        if amount_paid <= 0:
            invoice.status = Invoice.Status.ISSUED
        elif amount_paid < total:
            invoice.status = Invoice.Status.PARTIALLY_PAID
        else:
            invoice.status = Invoice.Status.PAID
    invoice.save(update_fields=["subtotal", "total", "amount_paid", "status", "updated_at"])
    return invoice


@transaction.atomic
def create_invoice(*, patient, care_episode, accounting_user, due_at=None, notes="", request=None):
    _require_accounting(accounting_user)
    if care_episode and care_episode.patient_id != patient.id:
        raise ValidationError("The selected care episode does not belong to this patient.")
    currency = HospitalProfile.objects.values_list("billing_currency", flat=True).first() or "XAF"
    invoice = Invoice.objects.create(
        invoice_number=_number("INV"),
        patient=patient,
        care_episode=care_episode,
        currency=currency,
        due_at=due_at,
        notes=notes,
        created_by=accounting_user,
    )
    record_audit_event(
        actor=accounting_user,
        request=request,
        action="billing.invoice.created",
        object_type="billing.Invoice",
        object_id=invoice.id,
        after={"patient_id": str(patient.id), "invoice_number": invoice.invoice_number},
    )
    return invoice


@transaction.atomic
def add_invoice_line(
    *,
    invoice,
    accounting_user,
    charge_item,
    description,
    quantity,
    unit_price,
    service_date,
    request=None,
):
    _require_accounting(accounting_user)
    locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if locked.status != Invoice.Status.DRAFT:
        raise ValidationError("Lines can only be changed while the invoice is in draft.")
    quantity = Decimal(quantity)
    unit_price = Decimal(unit_price)
    if quantity <= 0 or unit_price < 0:
        raise ValidationError("Quantity must be positive and price cannot be negative.")
    line = InvoiceLine.objects.create(
        invoice=locked,
        charge_item=charge_item,
        description=description,
        quantity=quantity,
        unit_price=unit_price,
        line_total=(quantity * unit_price).quantize(Decimal("0.01")),
        service_date=service_date,
    )
    _recalculate(locked)
    record_audit_event(
        actor=accounting_user,
        request=request,
        action="billing.invoice_line.created",
        object_type="billing.InvoiceLine",
        object_id=line.id,
        after={"invoice_id": str(locked.id), "line_total": str(line.line_total)},
    )
    return line


@transaction.atomic
def issue_invoice(*, invoice, accounting_user, due_at, request=None):
    _require_accounting(accounting_user)
    locked = Invoice.objects.select_for_update().select_related("patient").get(pk=invoice.pk)
    if locked.status != Invoice.Status.DRAFT:
        raise ValidationError("Only a draft invoice can be issued.")
    _recalculate(locked)
    if locked.total <= 0 or not locked.lines.exists():
        raise ValidationError("Add at least one positive charge before issuing.")
    now = timezone.now()
    locked.status = Invoice.Status.ISSUED
    locked.issued_at = now
    locked.due_at = due_at
    locked.save(update_fields=["status", "issued_at", "due_at", "updated_at"])
    accesses = GuardianAccess.objects.filter(
        patient=locked.patient,
        status=GuardianAccess.Status.ACTIVE,
        can_view_billing=True,
    ).select_related("guardian__user")
    for access in accesses:
        notify(
            recipient=access.guardian.user,
            actor=accounting_user,
            patient=locked.patient,
            category="INVOICE_ISSUED",
            severity=Notification.Severity.INFORMATION,
            title="Invoice available",
            body=f"Invoice {locked.invoice_number} is available for review.",
            route="/patient-guard/billing",
            dedupe_key=f"invoice-issued:{locked.id}:{access.guardian.user_id}",
        )
    record_audit_event(
        actor=accounting_user,
        request=request,
        action="billing.invoice.issued",
        object_type="billing.Invoice",
        object_id=locked.id,
        after={"total": str(locked.total), "due_at": due_at.isoformat()},
    )
    return locked


@transaction.atomic
def record_payment(
    *, invoice, accounting_user, amount, method, reference, received_at, request=None
):
    _require_accounting(accounting_user)
    locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    _recalculate(locked)
    if locked.status not in {Invoice.Status.ISSUED, Invoice.Status.PARTIALLY_PAID}:
        raise ValidationError("Payments can only be posted to an issued unpaid invoice.")
    amount = Decimal(amount)
    if amount <= 0 or amount > locked.outstanding_amount:
        raise ValidationError("Payment must be positive and cannot exceed the outstanding amount.")
    payment = Payment.objects.create(
        invoice=locked,
        receipt_number=_number("RCT"),
        amount=amount,
        method=method,
        reference=reference,
        received_at=received_at,
        recorded_by=accounting_user,
    )
    _recalculate(locked)
    record_audit_event(
        actor=accounting_user,
        request=request,
        action="billing.payment.posted",
        object_type="billing.Payment",
        object_id=payment.id,
        after={"invoice_id": str(locked.id), "amount": str(amount)},
    )
    return payment


@transaction.atomic
def reverse_payment(*, payment, accounting_user, reason, request=None):
    _require_accounting(accounting_user)
    locked = Payment.objects.select_for_update().select_related("invoice").get(pk=payment.pk)
    if locked.status != Payment.Status.POSTED:
        raise ValidationError("This payment has already been reversed.")
    if not reason.strip():
        raise ValidationError("A reversal reason is required.")
    locked.status = Payment.Status.REVERSED
    locked.reversed_at = timezone.now()
    locked.reversed_by = accounting_user
    locked.reversal_reason = reason
    locked.save(
        update_fields=[
            "status",
            "reversed_at",
            "reversed_by",
            "reversal_reason",
            "updated_at",
        ]
    )
    _recalculate(locked.invoice)
    record_audit_event(
        actor=accounting_user,
        request=request,
        action="billing.payment.reversed",
        object_type="billing.Payment",
        object_id=locked.id,
        reason=reason,
    )
    return locked


@transaction.atomic
def void_invoice(*, invoice, accounting_user, reason, request=None):
    _require_accounting(accounting_user)
    locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if locked.status == Invoice.Status.VOID:
        raise ValidationError("This invoice is already void.")
    if locked.payments.filter(status=Payment.Status.POSTED).exists():
        raise ValidationError("Reverse all posted payments before voiding the invoice.")
    if not reason.strip():
        raise ValidationError("A void reason is required.")
    locked.status = Invoice.Status.VOID
    locked.voided_at = timezone.now()
    locked.voided_by = accounting_user
    locked.void_reason = reason
    locked.save(update_fields=["status", "voided_at", "voided_by", "void_reason", "updated_at"])
    record_audit_event(
        actor=accounting_user,
        request=request,
        action="billing.invoice.voided",
        object_type="billing.Invoice",
        object_id=locked.id,
        reason=reason,
    )
    return locked
