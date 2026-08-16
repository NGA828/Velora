from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.billing.models import ChargeItem, Invoice, InvoiceLine, Payment


class BillingPatientSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    medical_record_number = serializers.CharField()
    full_name = serializers.CharField(source="get_full_name")
    date_of_birth = serializers.DateField()
    status = serializers.CharField()


class ChargeItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChargeItem
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class InvoiceLineSerializer(serializers.ModelSerializer):
    charge_item_name = serializers.CharField(
        source="charge_item.name", read_only=True, default=None
    )

    class Meta:
        model = InvoiceLine
        fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True)
    patient_name = serializers.CharField(source="invoice.patient.get_full_name", read_only=True)
    currency = serializers.CharField(source="invoice.currency", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.get_full_name", read_only=True)
    reversed_by_name = serializers.CharField(
        source="reversed_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = Payment
        fields = "__all__"


class InvoiceSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.get_full_name", read_only=True)
    medical_record_number = serializers.CharField(
        source="patient.medical_record_number", read_only=True
    )
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)
    lines = InvoiceLineSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    outstanding_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"


class InvoiceCreateSerializer(serializers.Serializer):
    patient = serializers.UUIDField()
    care_episode = serializers.UUIDField(required=False, allow_null=True)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class InvoiceLineCreateSerializer(serializers.Serializer):
    charge_item = serializers.PrimaryKeyRelatedField(
        queryset=ChargeItem.objects.filter(is_active=True), required=False, allow_null=True
    )
    description = serializers.CharField(max_length=240)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    service_date = serializers.DateField(default=timezone.localdate)


class InvoiceIssueSerializer(serializers.Serializer):
    due_at = serializers.DateTimeField()


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300)


class PaymentCreateSerializer(serializers.Serializer):
    invoice = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    method = serializers.ChoiceField(choices=Payment.Method.choices)
    reference = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    received_at = serializers.DateTimeField(default=timezone.now)
