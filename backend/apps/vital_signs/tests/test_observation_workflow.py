from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.hospital.models import Department
from apps.identity.models import UserRole
from apps.identity.tests.factories import create_staff
from apps.notifications.models import Notification
from apps.patients.models import Patient
from apps.patients.tests.test_registration_workflow import registration_payload
from apps.vital_signs.models import (
    VitalMetric,
    VitalObservation,
    VitalRule,
    VitalRuleEvaluation,
    VitalRuleSet,
)
from apps.vital_signs.services import activate_rule_set


def configured_patient():
    department = Department.objects.create(code="MED", name="Medicine")
    doctor, _ = create_staff(
        role=UserRole.DOCTOR, email="doctor@example.org", employee_number="DOC-001"
    )
    nurse, nurse_profile = create_staff(
        role=UserRole.NURSE, email="nurse@example.org", employee_number="NUR-001"
    )
    client = APIClient()
    client.force_authenticate(doctor)
    response = client.post(
        reverse("patients:patient-list"),
        registration_payload(nurse_profile.id, department.id),
        format="json",
    )
    return doctor, nurse, Patient.objects.get(pk=response.json()["id"])


@pytest.mark.django_db
def test_observation_is_unassessed_when_no_approved_rule_set_exists():
    _, nurse, patient = configured_patient()
    metric = VitalMetric.objects.create(code="LOCAL", name="Local measure", unit="u")
    client = APIClient()
    client.force_authenticate(nurse)

    response = client.post(
        reverse("vital_signs:vital-observation-list"),
        {"patient": str(patient.id), "values": [{"metric": str(metric.id), "value": "12"}]},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["status"] == VitalObservation.Status.UNASSESSED
    assert response.json()["rule_set_name_snapshot"] == ""
    assert Notification.objects.filter(category="CRITICAL_VITALS").count() == 0


@pytest.mark.django_db
def test_configured_rules_produce_explainable_stable_and_critical_results():
    doctor, nurse, patient = configured_patient()
    head, _ = create_staff(
        role=UserRole.HEAD_OF_SERVICE,
        email="head@example.org",
        employee_number="HOS-001",
    )
    metric = VitalMetric.objects.create(code="LOCAL", name="Local measure", unit="u")
    rule_set = VitalRuleSet.objects.create(name="Approved local rules", version=1)
    rule = VitalRule.objects.create(
        rule_set=rule_set,
        metric=metric,
        name="Local high-value rule",
        operator=VitalRule.Operator.GREATER_THAN,
        lower_value=Decimal("100"),
        explanation="The configured local high-value rule matched.",
    )
    activate_rule_set(rule_set=rule_set, actor=head)
    client = APIClient()
    client.force_authenticate(nurse)

    stable = client.post(
        reverse("vital_signs:vital-observation-list"),
        {"patient": str(patient.id), "values": [{"metric": str(metric.id), "value": "80"}]},
        format="json",
    )
    critical = client.post(
        reverse("vital_signs:vital-observation-list"),
        {"patient": str(patient.id), "values": [{"metric": str(metric.id), "value": "120"}]},
        format="json",
    )

    assert stable.status_code == 201
    assert stable.json()["status"] == VitalObservation.Status.STABLE
    assert critical.status_code == 201
    assert critical.json()["status"] == VitalObservation.Status.CRITICAL
    evaluation = VitalRuleEvaluation.objects.get(observation_id=critical.json()["id"], rule=rule)
    assert evaluation.matched is True
    assert evaluation.lower_value_snapshot == Decimal("100")
    assert evaluation.explanation == "The configured local high-value rule matched."
    assert Notification.objects.filter(
        recipient=doctor,
        patient=patient,
        category="CRITICAL_VITALS",
        severity="CRITICAL",
    ).exists()

    client.force_authenticate(doctor)
    history = client.get(
        reverse("vital_signs:vital-observation-list"), {"patient": str(patient.id)}
    )
    assert history.status_code == 200
    assert history.json()["pagination"]["count"] == 2


@pytest.mark.django_db
def test_doctor_and_unassigned_nurse_cannot_record_vitals():
    doctor, _, patient = configured_patient()
    unrelated, _ = create_staff(
        role=UserRole.NURSE,
        email="unrelated@example.org",
        employee_number="NUR-002",
    )
    metric = VitalMetric.objects.create(code="LOCAL", name="Local measure", unit="u")
    payload = {"patient": str(patient.id), "values": [{"metric": str(metric.id), "value": "12"}]}
    client = APIClient()

    client.force_authenticate(doctor)
    assert (
        client.post(
            reverse("vital_signs:vital-observation-list"), payload, format="json"
        ).status_code
        == 403
    )
    client.force_authenticate(unrelated)
    assert (
        client.post(
            reverse("vital_signs:vital-observation-list"), payload, format="json"
        ).status_code
        == 404
    )
    assert VitalObservation.objects.count() == 0
