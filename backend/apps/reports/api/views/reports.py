import csv
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import Invoice, Payment
from apps.hospital.models import (
    Bed,
    Department,
    ExternalHospital,
    HospitalProfile,
    Resource,
)
from apps.identity.models import StaffProfile, UserRole
from apps.patients.models import Patient
from apps.reports.permissions import AccountingOnly, HeadOfServiceOnly


class FinancialReportView(APIView):
    permission_classes = [AccountingOnly]

    def get(self, request):
        posted = Payment.objects.filter(status=Payment.Status.POSTED)
        issued = Invoice.objects.exclude(status__in=[Invoice.Status.DRAFT, Invoice.Status.VOID])
        collected = posted.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        billed = issued.aggregate(total=Sum("total"))["total"] or Decimal("0")
        outstanding = issued.aggregate(total=Sum("total"), paid=Sum("amount_paid"))
        outstanding_amount = (outstanding["total"] or Decimal("0")) - (
            outstanding["paid"] or Decimal("0")
        )
        by_method = list(
            posted.values("method")
            .annotate(count=Count("id"), total=Sum("amount"))
            .order_by("method")
        )
        by_status = list(
            Invoice.objects.values("status")
            .annotate(count=Count("id"), total=Sum("total"))
            .order_by("status")
        )
        currency = (
            HospitalProfile.objects.values_list("billing_currency", flat=True).first() or "XAF"
        )
        return Response(
            {
                "generated_at": timezone.now(),
                "currency": currency,
                "billed": billed,
                "collected": collected,
                "outstanding": outstanding_amount,
                "invoice_count": Invoice.objects.count(),
                "payment_count": posted.count(),
                "by_payment_method": by_method,
                "by_invoice_status": by_status,
            }
        )


class FinancialReportExportView(APIView):
    permission_classes = [AccountingOnly]

    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="velora-financial-report-{timezone.localdate().isoformat()}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(
            [
                "Invoice",
                "Patient MRN",
                "Status",
                "Issued at",
                "Due at",
                "Currency",
                "Total",
                "Paid",
                "Outstanding",
            ]
        )
        for invoice in Invoice.objects.select_related("patient").all():
            writer.writerow(
                [
                    invoice.invoice_number,
                    invoice.patient.medical_record_number,
                    invoice.status,
                    invoice.issued_at or "",
                    invoice.due_at or "",
                    invoice.currency,
                    invoice.total,
                    invoice.amount_paid,
                    invoice.outstanding_amount,
                ]
            )
        return response


class OperationalReportView(APIView):
    permission_classes = [HeadOfServiceOnly]

    def get(self, request):
        return Response(
            {
                "generated_at": timezone.now(),
                "staff": {
                    "doctors": StaffProfile.objects.filter(
                        user__role=UserRole.DOCTOR,
                        user__is_active=True,
                    ).count(),
                    "nurses": StaffProfile.objects.filter(
                        user__role=UserRole.NURSE,
                        user__is_active=True,
                    ).count(),
                },
                "patients": {
                    "total": Patient.objects.count(),
                    "registered_last_30_days": Patient.objects.filter(
                        created_at__gte=timezone.now() - timedelta(days=30)
                    ).count(),
                    "by_status": list(
                        Patient.objects.values("status")
                        .annotate(count=Count("id"))
                        .order_by("status")
                    ),
                },
                "operations": {
                    "departments": Department.objects.filter(is_active=True).count(),
                    "beds_available": Bed.objects.filter(status=Bed.Status.AVAILABLE).count(),
                    "beds_total": Bed.objects.count(),
                    "resources_unavailable": Resource.objects.filter(
                        status__in=[Resource.Status.UNAVAILABLE, Resource.Status.MAINTENANCE]
                    ).count(),
                    "external_hospitals": ExternalHospital.objects.filter(is_active=True).count(),
                },
            }
        )
