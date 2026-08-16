from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.billing.models import ChargeItem
from apps.billing.services import add_invoice_line, create_invoice, issue_invoice
from apps.identity.models import UserRole
from apps.identity.tests.factories import create_staff
from apps.monitoring.tests.test_monitoring_workflow import monitoring_context
from apps.patients.models import GuardianAccess


@pytest.mark.django_db
def test_guard_billing_visibility_requires_explicit_permission():
    _, _, guard, profile, patient = monitoring_context()
    accounting, _ = create_staff(
        role=UserRole.ACCOUNTING,
        email="accounts@example.org",
        employee_number="ACC-001",
    )
    charge = ChargeItem.objects.create(
        code="SVC",
        name="Service charge",
        category="SERVICE",
        default_unit_price=Decimal("20.00"),
    )
    invoice = create_invoice(
        patient=patient,
        care_episode=patient.care_episodes.get(status="ACTIVE"),
        accounting_user=accounting,
    )
    add_invoice_line(
        invoice=invoice,
        accounting_user=accounting,
        charge_item=charge,
        description="Service charge",
        quantity=Decimal("1"),
        unit_price=Decimal("20"),
        service_date=timezone.localdate(),
    )
    issue_invoice(
        invoice=invoice,
        accounting_user=accounting,
        due_at=timezone.now() + timedelta(days=7),
    )
    client = APIClient()
    client.force_authenticate(guard)

    hidden = client.get(reverse("billing:invoice-list"))
    assert hidden.json()["pagination"]["count"] == 0

    access = GuardianAccess.objects.get(patient=patient, guardian=profile)
    access.can_view_billing = True
    access.save(update_fields=["can_view_billing", "updated_at"])
    visible = client.get(reverse("billing:invoice-list"))
    assert visible.json()["pagination"]["count"] == 1
