from decimal import Decimal
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.hospital.models import Department, Bed, Room
from apps.identity.models import UserRole
from apps.identity.tests.factories import create_staff
from apps.patients.models import CareEpisode, Patient, PatientCareAssignment
from apps.vital_signs.models import VitalMetric, VitalRuleSet, VitalRule, IcuRecommendation, VitalObservation
from apps.vital_signs.services import activate_rule_set
from apps.patients.tests.test_registration_workflow import registration_payload


def setup_icu_patient():
    department = Department.objects.create(code="ICU-DEP", name="Intensive Care Dept")
    doctor, doc_profile = create_staff(
        role=UserRole.DOCTOR, email="icu_doc@example.org", employee_number="DOC-ICU-001"
    )
    nurse, nurse_profile = create_staff(
        role=UserRole.NURSE, email="icu_nurse@example.org", employee_number="NUR-ICU-001"
    )
    
    # Register patient
    client = APIClient()
    client.force_authenticate(doctor)
    response = client.post(
        reverse("patients:patient-list"),
        registration_payload(nurse_profile.id, department.id),
        format="json",
    )
    patient = Patient.objects.get(pk=response.json()["id"])
    
    # Configure critical rules
    head, _ = create_staff(role=UserRole.HEAD_OF_SERVICE, email="hos@example.org", employee_number="HOS-001")
    metric = VitalMetric.objects.get(code="TEMP")
    rule_set = VitalRuleSet.objects.create(name="Clinical Rules", version=1)
    VitalRule.objects.create(
        rule_set=rule_set,
        metric=metric,
        name="High Temp Alert",
        operator=VitalRule.Operator.GREATER_THAN,
        lower_value=Decimal("38.5"),
        explanation="High fever detected.",
    )
    activate_rule_set(rule_set=rule_set, actor=head)
    
    return doctor, doc_profile, nurse, patient, metric


@pytest.mark.django_db
def test_icu_recommendation_specialist_absent():
    doctor, doc_profile, nurse, patient, metric = setup_icu_patient()
    
    # Break doctor assignment to simulate specialist absence
    PatientCareAssignment.objects.filter(patient=patient, assignment_type=UserRole.DOCTOR).delete()
    
    client = APIClient()
    client.force_authenticate(nurse)
    
    response = client.post(
        reverse("vital_signs:vital-observation-list"),
        {
            "patient": str(patient.id),
            "values": [{"metric": str(metric.id), "value": "39.0"}]  # matches critical rule
        },
        format="json",
    )
    
    assert response.status_code == 201
    obs_id = response.json()["id"]
    rec = IcuRecommendation.objects.get(observation_id=obs_id)
    assert rec.eligible is True
    assert rec.specialist_status == "ABSENT"
    assert "No specialist physician is currently assigned" in rec.explanation
    assert rec.score < 100


@pytest.mark.django_db
def test_icu_recommendation_specialist_overloaded():
    doctor, doc_profile, nurse, patient, metric = setup_icu_patient()
    
    # Register 5 additional patients via the API to overload the doctor
    reg_client = APIClient()
    reg_client.force_authenticate(doctor)
    _, nurse_profile = create_staff(
        role=UserRole.NURSE, email="extra_nurse@example.org", employee_number="NUR-EX-001"
    )
    dept = patient.care_episodes.first().department
    for i in range(5):
        payload = registration_payload(nurse_profile.id, dept.id)
        payload["first_name"] = f"Dummy{i}"
        payload["last_name"] = "Overload"
        reg_client.post(reverse("patients:patient-list"), payload, format="json")
        
    client = APIClient()
    client.force_authenticate(nurse)
    response = client.post(
        reverse("vital_signs:vital-observation-list"),
        {
            "patient": str(patient.id),
            "values": [{"metric": str(metric.id), "value": "39.0"}]
        },
        format="json",
    )
    
    assert response.status_code == 201
    obs_id = response.json()["id"]
    rec = IcuRecommendation.objects.get(observation_id=obs_id)
    assert rec.eligible is True
    assert rec.specialist_status == "OVERLOADED"
    assert "is overloaded with > 5 active assignments" in rec.explanation


@pytest.mark.django_db
def test_icu_recommendation_icu_bed_overloaded():
    doctor, doc_profile, nurse, patient, metric = setup_icu_patient()
    
    # Create ICU Bed capacity (1 bed occupied)
    episode = patient.care_episodes.filter(status="ACTIVE").first()
    room = Room.objects.create(code="ICU-101", department=episode.department, room_type="ICU")
    Bed.objects.create(code="BED-1", room=room, status=Bed.Status.OCCUPIED)
    
    client = APIClient()
    client.force_authenticate(nurse)
    response = client.post(
        reverse("vital_signs:vital-observation-list"),
        {
            "patient": str(patient.id),
            "values": [{"metric": str(metric.id), "value": "39.0"}]
        },
        format="json",
    )
    
    assert response.status_code == 201
    obs_id = response.json()["id"]
    rec = IcuRecommendation.objects.get(observation_id=obs_id)
    assert rec.eligible is True
    assert rec.icu_bed_status == "OVERLOADED"
    assert "ICU beds are at 100% capacity" in rec.explanation
