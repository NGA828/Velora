from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.identity.models import UserRole
from apps.identity.tests.factories import create_staff
from apps.vital_signs.models import VitalMetric, VitalRuleSet


@pytest.mark.django_db
def test_rule_set_requires_rules_before_activation_and_records_no_threshold_defaults():
    head, _ = create_staff(role=UserRole.HEAD_OF_SERVICE, email="head@example.org")
    client = APIClient()
    client.force_authenticate(head)

    metric = client.post(
        reverse("vital_signs:vital-metric-list"),
        {"code": "LOCAL_METRIC", "name": "Local metric", "unit": "unit", "decimal_places": 1},
        format="json",
    )
    assert metric.status_code == 201
    assert VitalMetric.objects.get().rules.count() == 0

    rule_set = client.post(
        reverse("vital_signs:vital-rule-set-list"),
        {"name": "Hospital approved rules", "version": 1, "description": "Approved locally"},
        format="json",
    )
    assert rule_set.status_code == 201
    rule_set_id = rule_set.json()["id"]

    rejected = client.post(
        reverse("vital_signs:vital-rule-set-activate", kwargs={"pk": rule_set_id})
    )
    assert rejected.status_code == 400

    invalid_rule = client.post(
        reverse("vital_signs:vital-rule-list"),
        {
            "rule_set": rule_set_id,
            "metric": metric.json()["id"],
            "name": "Incomplete range",
            "operator": "BETWEEN",
            "lower_value": "10.0",
            "explanation": "Configured explanation",
        },
        format="json",
    )
    assert invalid_rule.status_code == 400


@pytest.mark.django_db
def test_activating_new_rule_set_retires_previous_version():
    head, _ = create_staff(role=UserRole.HEAD_OF_SERVICE, email="head@example.org")
    metric = VitalMetric.objects.create(code="M", name="Metric", unit="u")
    first = VitalRuleSet.objects.create(name="Rules", version=1)
    second = VitalRuleSet.objects.create(name="Rules", version=2)
    for rule_set in [first, second]:
        rule_set.rules.create(
            metric=metric,
            name=f"Critical rule v{rule_set.version}",
            operator="GT",
            lower_value=Decimal("5.0"),
            explanation="Configured by clinical governance",
        )

    client = APIClient()
    client.force_authenticate(head)
    first_result = client.post(
        reverse("vital_signs:vital-rule-set-activate", kwargs={"pk": first.id})
    )
    second_result = client.post(
        reverse("vital_signs:vital-rule-set-activate", kwargs={"pk": second.id})
    )

    assert first_result.status_code == 200
    assert second_result.status_code == 200
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.status == VitalRuleSet.Status.RETIRED
    assert first.effective_to is not None
    assert second.status == VitalRuleSet.Status.ACTIVE
    assert second.approved_by == head


@pytest.mark.django_db
def test_doctor_can_read_but_not_change_vital_rules():
    doctor, _ = create_staff(role=UserRole.DOCTOR, email="doctor@example.org")
    client = APIClient()
    client.force_authenticate(doctor)

    assert client.get(reverse("vital_signs:vital-metric-list")).status_code == 200
    assert (
        client.post(
            reverse("vital_signs:vital-metric-list"),
            {"code": "M", "name": "Metric", "unit": "u"},
            format="json",
        ).status_code
        == 403
    )
