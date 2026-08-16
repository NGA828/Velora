import pytest
from rest_framework.test import APIClient

from apps.identity.models import UserRole
from apps.identity.tests.factories import create_staff, create_user


@pytest.mark.django_db
def test_sensitive_endpoint_role_boundaries_are_enforced():
    admin, _ = create_staff(
        role=UserRole.ADMIN,
        email="admin@example.org",
        employee_number="ADM-001",
    )
    head, _ = create_staff(
        role=UserRole.HEAD_OF_SERVICE,
        email="head@example.org",
        employee_number="HOS-001",
    )
    doctor, _ = create_staff(
        role=UserRole.DOCTOR,
        email="doctor@example.org",
        employee_number="DOC-001",
    )
    nurse, _ = create_staff(
        role=UserRole.NURSE,
        email="nurse@example.org",
        employee_number="NUR-001",
    )
    accounting, _ = create_staff(
        role=UserRole.ACCOUNTING,
        email="accounting@example.org",
        employee_number="ACC-001",
    )
    guard = create_user(role=UserRole.PATIENT_GUARD, email="guard@example.org")

    cases = [
        (admin, "/api/v1/patients/", 403),
        (admin, "/api/v1/medical-files/", 403),
        (admin, "/api/v1/system/dashboard/", 200),
        (head, "/api/v1/patients/", 403),
        (head, "/api/v1/hospital/departments/", 200),
        (doctor, "/api/v1/system/dashboard/", 403),
        (doctor, "/api/v1/billing/patients/", 403),
        (nurse, "/api/v1/billing/patients/", 403),
        (accounting, "/api/v1/patients/", 403),
        (accounting, "/api/v1/invoices/", 200),
        (guard, "/api/v1/hospital/departments/", 403),
        (guard, "/api/v1/vital-observations/", 403),
    ]
    for user, path, expected in cases:
        client = APIClient()
        client.force_authenticate(user)
        response = client.get(path)
        assert response.status_code == expected, (user.role, path, response.content)


@pytest.mark.django_db
def test_anonymous_user_gets_no_protected_collections():
    client = APIClient()
    for path in [
        "/api/v1/patients/",
        "/api/v1/invoices/",
        "/api/v1/conversations/",
        "/api/v1/system/dashboard/",
    ]:
        assert client.get(path).status_code == 401
