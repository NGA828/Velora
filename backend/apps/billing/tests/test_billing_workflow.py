from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.billing.models import Invoice, Payment
from apps.hospital.models import Department
from apps.identity.models import UserRole
from apps.identity.tests.factories import create_staff
from apps.patients.models import Patient
from apps.patients.tests.test_registration_workflow import registration_payload


def billing_context():
    department = Department.objects.create(code="MED", name="Medicine")
    doctor, _ = create_staff(
        role=UserRole.DOCTOR, email="doctor@example.org", employee_number="DOC-001"
    )
    _, nurse_profile = create_staff(
        role=UserRole.NURSE, email="nurse@example.org", employee_number="NUR-001"
    )
    accounting, _ = create_staff(
        role=UserRole.ACCOUNTING,
        email="accounts@example.org",
        employee_number="ACC-001",
    )
    client = APIClient()
    client.force_authenticate(doctor)
    response = client.post(
        reverse("patients:patient-list"),
        registration_payload(nurse_profile.id, department.id),
        format="json",
    )
    return doctor, accounting, Patient.objects.get(pk=response.json()["id"])


@pytest.mark.django_db
def test_invoice_issue_payment_and_reversal_recalculate_status():
    _, accounting, patient = billing_context()
    client = APIClient()
    client.force_authenticate(accounting)
    charge = client.post(
        reverse("billing:charge-item-list"),
        {
            "code": "ROOM-DAY",
            "name": "Room daily charge",
            "category": "ROOM",
            "default_unit_price": "100.00",
            "description": "Configured room charge",
            "is_active": True,
        },
        format="json",
    )
    assert charge.status_code == 201
    invoice = client.post(
        reverse("billing:invoice-list"),
        {"patient": str(patient.id), "notes": "Billing test"},
        format="json",
    )
    assert invoice.status_code == 201
    invoice_id = invoice.json()["id"]
    line = client.post(
        reverse("billing:invoice-add-line", kwargs={"pk": invoice_id}),
        {
            "charge_item": charge.json()["id"],
            "description": "Two room days",
            "quantity": "2",
            "unit_price": "100.00",
            "service_date": timezone.localdate().isoformat(),
        },
        format="json",
    )
    assert line.status_code == 200
    assert line.json()["total"] == "200.00"
    issued = client.post(
        reverse("billing:invoice-issue", kwargs={"pk": invoice_id}),
        {"due_at": (timezone.now() + timedelta(days=14)).isoformat()},
        format="json",
    )
    assert issued.json()["status"] == Invoice.Status.ISSUED

    first_payment = client.post(
        reverse("billing:payment-list"),
        {
            "invoice": invoice_id,
            "amount": "75.00",
            "method": "MOBILE_MONEY",
            "reference": "MM-001",
        },
        format="json",
    )
    assert first_payment.status_code == 201
    invoice_record = Invoice.objects.get(pk=invoice_id)
    assert invoice_record.currency == "XAF"
    assert invoice_record.status == Invoice.Status.PARTIALLY_PAID
    assert invoice_record.amount_paid == 75

    reversed_payment = client.post(
        reverse("billing:payment-reverse", kwargs={"pk": first_payment.json()["id"]}),
        {"reason": "Payment provider reversal"},
        format="json",
    )
    assert reversed_payment.status_code == 200
    invoice_record.refresh_from_db()
    assert invoice_record.status == Invoice.Status.ISSUED
    assert invoice_record.amount_paid == 0
    assert Payment.objects.get().status == Payment.Status.REVERSED


@pytest.mark.django_db
def test_accounting_patient_lookup_excludes_clinical_fields_and_other_roles_are_denied():
    doctor, accounting, patient = billing_context()
    client = APIClient()
    client.force_authenticate(accounting)
    response = client.get(reverse("billing:patient-list"), {"search": patient.last_name})
    assert response.status_code == 200
    assert response.json()[0]["medical_record_number"] == patient.medical_record_number
    assert "address" not in response.json()[0]
    assert "diagnoses" not in response.json()[0]

    client.force_authenticate(doctor)
    assert client.get(reverse("billing:patient-list")).status_code == 403
    assert client.get(reverse("billing:invoice-list")).status_code == 403
