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
    assert stable.json()["stability_percent"] == 100
    assert stable.json()["criticality_percent"] == 0
    assert critical.json()["stability_percent"] == 0
    assert critical.json()["criticality_percent"] == 100
    assert critical.json()["assessed_metric_count"] == 1
    assert critical.json()["critical_metric_count"] == 1


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


@pytest.mark.django_db
def test_observation_score_uses_configured_rules_and_ignores_unscored_weight():
    doctor, nurse, patient = configured_patient()
    head, _ = create_staff(
        role=UserRole.HEAD_OF_SERVICE,
        email="head@example.org",
        employee_number="HOS-001",
    )
    pulse = VitalMetric.objects.get(code="PULSE")
    respiration = VitalMetric.objects.get(code="RR")
    weight = VitalMetric.objects.get(code="WT")
    weight.contributes_to_assessment = False
    weight.save(update_fields=["contributes_to_assessment", "updated_at"])
    rule_set = VitalRuleSet.objects.create(name="Adult vital reference", version=1)
    VitalRule.objects.create(
        rule_set=rule_set,
        metric=pulse,
        name="Tachycardia",
        operator=VitalRule.Operator.GREATER_THAN,
        lower_value=Decimal("100"),
        explanation="Pulse is above the configured adult resting range.",
    )
    VitalRule.objects.create(
        rule_set=rule_set,
        metric=respiration,
        name="Tachypnea",
        operator=VitalRule.Operator.GREATER_THAN,
        lower_value=Decimal("20"),
        explanation="Respiration rate is above the configured adult resting range.",
    )
    activate_rule_set(rule_set=rule_set, actor=head)
    client = APIClient()
    client.force_authenticate(nurse)

    response = client.post(
        reverse("vital_signs:vital-observation-list"),
        {
            "patient": str(patient.id),
            "values": [
                {"metric": str(pulse.id), "value": "118"},
                {"metric": str(respiration.id), "value": "16"},
                {"metric": str(weight.id), "value": "68.5"},
            ],
        },
        format="json",
    )

    payload = response.json()
    assert response.status_code == 201
    assert payload["status"] == VitalObservation.Status.CRITICAL
    assert payload["stability_percent"] == 50
    assert payload["criticality_percent"] == 50
    assert payload["assessed_metric_count"] == 2
    assert payload["critical_metric_count"] == 1
    values = {item["metric_code"]: item for item in payload["values"]}
    assert values["PULSE"]["is_critical"] is True
    assert values["RR"]["is_critical"] is False
    assert values["WT"]["contributes_to_assessment"] is False
    assert values["WT"]["is_critical"] is False

    client.force_authenticate(doctor)
    listing = client.get(reverse("patients:patient-list")).json()["data"][0]
    assert listing["latest_vital_status"] == VitalObservation.Status.CRITICAL
    assert listing["latest_vital_stability_percent"] == 50
    assert listing["latest_vital_criticality_percent"] == 50


def test_compute_stability_score_returns_percentages():
    from apps.vital_signs.services import compute_stability_score

    assert compute_stability_score(assessed_count=0, critical_count=0) == (None, None)
    assert compute_stability_score(assessed_count=5, critical_count=0) == (100, 0)
    assert compute_stability_score(assessed_count=5, critical_count=1) == (80, 20)
    assert compute_stability_score(assessed_count=5, critical_count=5) == (0, 100)
    assert compute_stability_score(assessed_count=3, critical_count=1) == (67, 33)
