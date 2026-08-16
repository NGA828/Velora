import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent, SystemHeartbeat
from apps.identity.models import UserRole
from apps.identity.tests.factories import create_staff


@pytest.mark.django_db
def test_admin_system_dashboard_and_redacted_audit_do_not_expose_snapshots():
    admin, _ = create_staff(
        role=UserRole.ADMIN,
        email="admin@example.org",
        employee_number="ADM-001",
    )
    admin.is_staff = True
    admin.save(update_fields=["is_staff", "updated_at"])
    AuditEvent.objects.create(
        actor=admin,
        action="clinical.test",
        object_type="clinical_records.ClinicalNote",
        object_id="record-one",
        before_snapshot={"body": "sensitive"},
        after_snapshot={"body": "more sensitive"},
    )
    SystemHeartbeat.objects.create(
        service="medication-reminder-worker",
        status="HEALTHY",
        last_seen_at=timezone.now(),
    )
    client = APIClient()
    client.force_authenticate(admin)

    dashboard = client.get(reverse("reports:system-dashboard"))
    audit = client.get(reverse("reports:system-audit-list"))

    assert dashboard.status_code == 200
    assert dashboard.json()["database"]["healthy"] is True
    assert dashboard.json()["scheduler"]["healthy"] is True
    assert audit.status_code == 200
    event = audit.json()["data"][0]
    assert "before_snapshot" not in event
    assert "after_snapshot" not in event
    assert "sensitive" not in str(event)


@pytest.mark.django_db
def test_admin_can_suspend_other_user_but_not_self():
    admin, _ = create_staff(
        role=UserRole.ADMIN,
        email="admin@example.org",
        employee_number="ADM-001",
    )
    nurse, _ = create_staff(
        role=UserRole.NURSE,
        email="nurse@example.org",
        employee_number="NUR-001",
    )
    client = APIClient()
    client.force_authenticate(admin)

    updated = client.patch(
        reverse("reports:system-user-detail", kwargs={"pk": nurse.id}),
        {"is_active": False},
        format="json",
    )
    assert updated.status_code == 200
    nurse.refresh_from_db()
    assert nurse.is_active is False
    self_blocked = client.patch(
        reverse("reports:system-user-detail", kwargs={"pk": admin.id}),
        {"is_active": False},
        format="json",
    )
    assert self_blocked.status_code == 400


@pytest.mark.django_db
def test_reports_are_strictly_role_scoped():
    accounting, _ = create_staff(
        role=UserRole.ACCOUNTING,
        email="accounts@example.org",
        employee_number="ACC-001",
    )
    head, _ = create_staff(
        role=UserRole.HEAD_OF_SERVICE,
        email="head@example.org",
        employee_number="HOS-001",
    )
    client = APIClient()
    client.force_authenticate(accounting)
    assert client.get(reverse("reports:financial")).status_code == 200
    assert client.get(reverse("reports:operational")).status_code == 403
    client.force_authenticate(head)
    assert client.get(reverse("reports:operational")).status_code == 200
    assert client.get(reverse("reports:financial")).status_code == 403
