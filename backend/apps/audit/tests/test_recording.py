import pytest

from apps.audit.services import record_audit_event
from apps.identity.models import UserRole
from apps.identity.tests.factories import create_staff


@pytest.mark.django_db
def test_audit_service_redacts_sensitive_fields():
    user, _ = create_staff(role=UserRole.ADMIN)

    event = record_audit_event(
        actor=user,
        action="test.action",
        object_type="test.Object",
        object_id="one",
        after={"email": user.email, "password": "must-not-be-recorded"},
    )

    assert event.after_snapshot["email"] == user.email
    assert event.after_snapshot["password"] == "[REDACTED]"
