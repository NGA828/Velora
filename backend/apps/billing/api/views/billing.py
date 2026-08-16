from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.billing.api.serializers import (
    BillingPatientSerializer,
    ChargeItemSerializer,
    InvoiceCreateSerializer,
    InvoiceIssueSerializer,
    InvoiceLineCreateSerializer,
    InvoiceSerializer,
    PaymentCreateSerializer,
    PaymentSerializer,
    ReasonSerializer,
)
from apps.billing.models import ChargeItem, Invoice, Payment
from apps.billing.permissions import AccountingOnly, AccountingPermission
from apps.billing.services import (
    add_invoice_line,
    create_invoice,
    issue_invoice,
    record_payment,
    reverse_payment,
    void_invoice,
)
from apps.common.throttling import ActionScopedThrottleMixin
from apps.common.viewsets import AuditedNoDestroyModelViewSet
from apps.hospital.models import HospitalProfile
from apps.identity.models import UserRole
from apps.patients.models import CareEpisode, GuardianAccess, Patient


def _service_error(exc):
    raise serializers.ValidationError({"detail": exc.messages}) from exc


def invoices_visible_to(user):
    queryset = Invoice.objects.all()
    if user.role == UserRole.PATIENT_GUARD:
        queryset = queryset.filter(
            patient__guardian_accesses__guardian__user=user,
            patient__guardian_accesses__status=GuardianAccess.Status.ACTIVE,
            patient__guardian_accesses__can_view_billing=True,
        ).exclude(status=Invoice.Status.DRAFT)
    return queryset.distinct()


def full_invoices(user):
    return (
        invoices_visible_to(user)
        .select_related("patient", "care_episode", "created_by")
        .prefetch_related("lines__charge_item", "payments__recorded_by", "payments__reversed_by")
    )


class BillingPatientListView(APIView):
    permission_classes = [AccountingOnly]

    def get(self, request):
        patients = Patient.objects.exclude(status=Patient.Status.ARCHIVED)
        search = request.query_params.get("search", "").strip()
        if search:
            from django.db.models import Q

            patients = patients.filter(
                Q(medical_record_number__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        return Response(BillingPatientSerializer(patients[:100], many=True).data)


class BillingDashboardView(APIView):
    permission_classes = [AccountingOnly]

    def get(self, request):
        today = timezone.localdate()
        posted_today = Payment.objects.filter(
            status=Payment.Status.POSTED,
            received_at__date=today,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        outstanding = Invoice.objects.filter(
            status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIALLY_PAID]
        ).aggregate(total=Sum("total"), paid=Sum("amount_paid"))
        outstanding_amount = (outstanding["total"] or Decimal("0")) - (
            outstanding["paid"] or Decimal("0")
        )
        currency = (
            HospitalProfile.objects.values_list("billing_currency", flat=True).first() or "XAF"
        )
        return Response(
            {
                "currency": currency,
                "draft_invoices": Invoice.objects.filter(status=Invoice.Status.DRAFT).count(),
                "issued_unpaid": Invoice.objects.filter(
                    status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIALLY_PAID]
                ).count(),
                "overdue_invoices": Invoice.objects.filter(
                    status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIALLY_PAID],
                    due_at__lt=timezone.now(),
                ).count(),
                "payments_today": posted_today,
                "outstanding_amount": outstanding_amount,
                "recent_invoices": InvoiceSerializer(
                    full_invoices(request.user)[:5], many=True
                ).data,
            }
        )


class ChargeItemViewSet(AuditedNoDestroyModelViewSet):
    serializer_class = ChargeItemSerializer
    permission_classes = [AccountingOnly]
    queryset = ChargeItem.objects.all()


class InvoiceViewSet(ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [AccountingPermission]

    def get_queryset(self):
        queryset = full_invoices(self.request.user)
        patient = self.request.query_params.get("patient")
        return queryset.filter(patient_id=patient) if patient else queryset

    def create(self, request, *args, **kwargs):
        serializer = InvoiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        patient = get_object_or_404(Patient, pk=data["patient"])
        episode = None
        if data.get("care_episode"):
            episode = get_object_or_404(CareEpisode, pk=data["care_episode"], patient=patient)
        try:
            invoice = create_invoice(
                patient=patient,
                care_episode=episode,
                accounting_user=request.user,
                due_at=data.get("due_at"),
                notes=data["notes"],
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(
            InvoiceSerializer(full_invoices(request.user).get(pk=invoice.pk)).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="lines")
    def add_line(self, request, pk=None):
        serializer = InvoiceLineCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            add_invoice_line(
                invoice=self.get_object(),
                accounting_user=request.user,
                request=request,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(InvoiceSerializer(full_invoices(request.user).get(pk=pk)).data)

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        serializer = InvoiceIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            issue_invoice(
                invoice=self.get_object(),
                accounting_user=request.user,
                due_at=serializer.validated_data["due_at"],
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(InvoiceSerializer(full_invoices(request.user).get(pk=pk)).data)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            void_invoice(
                invoice=self.get_object(),
                accounting_user=request.user,
                reason=serializer.validated_data["reason"],
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(InvoiceSerializer(full_invoices(request.user).get(pk=pk)).data)


class PaymentViewSet(ActionScopedThrottleMixin, ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    throttle_scope_by_action = {"create": "payment_post", "reverse": "payment_post"}
    permission_classes = [AccountingPermission]

    def get_queryset(self):
        queryset = Payment.objects.filter(
            invoice__in=invoices_visible_to(self.request.user)
        ).select_related("invoice__patient", "recorded_by", "reversed_by")
        invoice = self.request.query_params.get("invoice")
        return queryset.filter(invoice_id=invoice) if invoice else queryset

    def create(self, request, *args, **kwargs):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = get_object_or_404(Invoice, pk=serializer.validated_data["invoice"])
        data = dict(serializer.validated_data)
        data.pop("invoice")
        try:
            payment = record_payment(
                invoice=invoice,
                accounting_user=request.user,
                request=request,
                **data,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = reverse_payment(
                payment=self.get_object(),
                accounting_user=request.user,
                reason=serializer.validated_data["reason"],
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(PaymentSerializer(payment).data)
