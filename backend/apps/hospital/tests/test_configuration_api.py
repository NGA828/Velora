import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.hospital.models import Department, HospitalProfile, Resource
from apps.identity.models import UserRole
from apps.identity.tests.factories import create_staff


@pytest.mark.django_db
def test_head_of_service_configures_profile_and_doctor_has_read_only_access():
    head, _ = create_staff(role=UserRole.HEAD_OF_SERVICE, email="head@example.org")
    doctor, _ = create_staff(role=UserRole.DOCTOR, email="doctor@example.org")
    client = APIClient()
    client.force_authenticate(head)
    payload = {
        "legal_name": "Velora Central Hospital Ltd",
        "display_name": "Velora Central Hospital",
        "registration_number": "HSP-001",
        "address": "12 Care Avenue",
        "city": "Yaoundé",
        "region": "Centre",
        "country": "CM",
        "email": "hospital@example.org",
        "phone": "+237600000001",
        "timezone": "Africa/Lagos",
    }

    created = client.put(reverse("hospital:profile"), payload, format="json")
    assert created.status_code == 201
    assert HospitalProfile.objects.count() == 1

    client.force_authenticate(doctor)
    readable = client.get(reverse("hospital:profile"))
    forbidden = client.patch(
        reverse("hospital:profile"), {"display_name": "Changed"}, format="json"
    )
    assert readable.status_code == 200
    assert readable.json()["data"]["display_name"] == "Velora Central Hospital"
    assert forbidden.status_code == 403


@pytest.mark.django_db
def test_resource_validation_and_no_hard_delete():
    head, _ = create_staff(role=UserRole.HEAD_OF_SERVICE, email="head@example.org")
    department = Department.objects.create(code="ER", name="Emergency")
    client = APIClient()
    client.force_authenticate(head)

    invalid = client.post(
        reverse("hospital:resource-list"),
        {
            "asset_code": "MON-001",
            "name": "Patient monitor",
            "category": "EQUIPMENT",
            "department": department.id,
            "quantity_total": 2,
            "quantity_available": 3,
            "status": "AVAILABLE",
        },
        format="json",
    )
    assert invalid.status_code == 400
    assert Resource.objects.count() == 0

    valid = client.post(
        reverse("hospital:resource-list"),
        {
            "asset_code": "MON-001",
            "name": "Patient monitor",
            "category": "EQUIPMENT",
            "department": department.id,
            "quantity_total": 2,
            "quantity_available": 2,
            "status": "AVAILABLE",
        },
        format="json",
    )
    assert valid.status_code == 201

    deleted = client.delete(reverse("hospital:resource-detail", kwargs={"pk": valid.json()["id"]}))
    assert deleted.status_code == 405
    assert Resource.objects.count() == 1


@pytest.mark.django_db
def test_patient_guard_cannot_browse_hospital_configuration():
    guard = create_staff(role=UserRole.NURSE, email="nurse@example.org")[0]
    guard.role = UserRole.PATIENT_GUARD
    guard.save(update_fields=["role"])
    client = APIClient()
    client.force_authenticate(guard)

    response = client.get(reverse("hospital:department-list"))

    assert response.status_code == 403
