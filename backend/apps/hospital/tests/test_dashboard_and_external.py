import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.hospital.models import ExternalHospital, Specialty
from apps.identity.models import UserRole
from apps.identity.tests.factories import create_staff


@pytest.mark.django_db
def test_external_hospital_readiness_is_based_on_stored_capabilities():
    head, _ = create_staff(role=UserRole.HEAD_OF_SERVICE, email="head@example.org")
    specialty = Specialty.objects.create(code="CARD", name="Cardiology")
    client = APIClient()
    client.force_authenticate(head)

    hospital_response = client.post(
        reverse("hospital:external-hospital-list"),
        {
            "name": "Partner Medical Centre",
            "address": "20 Partner Road",
            "city": "Yaoundé",
            "country": "CM",
            "phone": "+237600000002",
            "transfer_email": "transfer@partner.example.org",
        },
        format="json",
    )
    assert hospital_response.status_code == 201
    hospital_id = hospital_response.json()["id"]

    before = client.get(reverse("hospital:external-hospital-detail", kwargs={"pk": hospital_id}))
    assert before.json()["transfer_ready"] is False

    capability = client.post(
        reverse("hospital:external-hospital-specialty-list"),
        {
            "external_hospital": hospital_id,
            "specialty": specialty.id,
            "availability_status": "AVAILABLE",
        },
        format="json",
    )
    assert capability.status_code == 201

    after = client.get(reverse("hospital:external-hospital-detail", kwargs={"pk": hospital_id}))
    assert after.json()["transfer_ready"] is True
    assert after.json()["specialty_count"] == 1


@pytest.mark.django_db
def test_dashboard_reports_real_configuration_attention_counts():
    head, _ = create_staff(role=UserRole.HEAD_OF_SERVICE, email="head@example.org")
    ExternalHospital.objects.create(
        name="Incomplete Hospital",
        address="Unknown",
        city="Yaoundé",
        country="CM",
        phone="+237600000003",
        transfer_email="",
    )
    client = APIClient()
    client.force_authenticate(head)

    response = client.get(reverse("hospital:dashboard"))

    assert response.status_code == 200
    assert response.json()["transfers"]["external_hospitals"] == 1
    assert response.json()["transfers"]["incomplete_profiles"] == 1
    assert response.json()["hospital_profile_configured"] is False
