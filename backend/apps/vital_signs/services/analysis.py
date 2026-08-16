from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.patients.models import CareEpisode, Patient, PatientCareAssignment
from apps.vital_signs.models import (
    VitalObservation,
    VitalRule,
    VitalRuleEvaluation,
    VitalRuleSet,
    VitalValue,
)


def rule_matches(*, rule: VitalRule, value: Decimal) -> bool:
    if rule.operator == VitalRule.Operator.LESS_THAN:
        return value < rule.upper_value
    if rule.operator == VitalRule.Operator.LESS_THAN_OR_EQUAL:
        return value <= rule.upper_value
    if rule.operator == VitalRule.Operator.GREATER_THAN:
        return value > rule.lower_value
    if rule.operator == VitalRule.Operator.GREATER_THAN_OR_EQUAL:
        return value >= rule.lower_value
    if rule.operator == VitalRule.Operator.BETWEEN:
        return rule.lower_value <= value <= rule.upper_value
    if rule.operator == VitalRule.Operator.OUTSIDE:
        return value < rule.lower_value or value > rule.upper_value
    raise ValidationError(f"Unsupported vital rule operator: {rule.operator}")


@transaction.atomic
def record_and_analyze_observation(
    *,
    patient: Patient,
    nurse,
    observed_at,
    values: list[dict],
    notes: str = "",
    request=None,
) -> VitalObservation:
    if not PatientCareAssignment.objects.filter(
        patient=patient,
        staff__user=nurse,
        assignment_type=PatientCareAssignment.AssignmentType.NURSE,
        ends_at__isnull=True,
    ).exists():
        raise ValidationError("Only an assigned Nurse can record vital signs for this patient.")
    episode = patient.care_episodes.filter(status=CareEpisode.Status.ACTIVE).first()
    if not episode:
        raise ValidationError("The patient has no active care episode.")
    if not values:
        raise ValidationError("Record at least one vital measurement.")

    observation = VitalObservation.objects.create(
        patient=patient,
        care_episode=episode,
        observed_at=observed_at,
        recorded_by=nurse,
        notes=notes,
    )
    observed_values = [
        VitalValue.objects.create(
            observation=observation,
            metric=item["metric"],
            value=item["value"],
        )
        for item in values
    ]

    rule_set = VitalRuleSet.objects.filter(status=VitalRuleSet.Status.ACTIVE).first()
    analyzed_at = timezone.now()
    if not rule_set:
        observation.status = VitalObservation.Status.UNASSESSED
        observation.analyzed_at = analyzed_at
        observation.save(update_fields=["status", "analyzed_at", "updated_at"])
        _audit_observation(observation=observation, actor=nurse, request=request)
        return observation

    rules = VitalRule.objects.filter(
        rule_set=rule_set,
        is_active=True,
        metric__is_active=True,
        metric_id__in=[item.metric_id for item in observed_values],
    ).select_related("metric")
    rules_by_metric = defaultdict(list)
    for rule in rules:
        rules_by_metric[rule.metric_id].append(rule)

    fully_assessed = True
    critical_explanations: list[str] = []
    for observed_value in observed_values:
        metric_rules = rules_by_metric[observed_value.metric_id]
        if not metric_rules:
            fully_assessed = False
            continue
        for rule in metric_rules:
            matched = rule_matches(rule=rule, value=observed_value.value)
            explanation = (
                rule.explanation
                if matched
                else f"{rule.metric.name} did not match the configured rule ‘{rule.name}’."
            )
            VitalRuleEvaluation.objects.create(
                observation=observation,
                value=observed_value,
                rule=rule,
                matched=matched,
                measured_value=observed_value.value,
                rule_name_snapshot=rule.name,
                metric_name_snapshot=rule.metric.name,
                metric_unit_snapshot=rule.metric.unit,
                operator_snapshot=rule.operator,
                lower_value_snapshot=rule.lower_value,
                upper_value_snapshot=rule.upper_value,
                explanation=explanation,
            )
            if matched:
                critical_explanations.append(rule.explanation)

    if critical_explanations:
        status = VitalObservation.Status.CRITICAL
    elif fully_assessed:
        status = VitalObservation.Status.STABLE
    else:
        status = VitalObservation.Status.UNASSESSED
    observation.status = status
    observation.analyzed_at = analyzed_at
    observation.rule_set = rule_set
    observation.rule_set_name_snapshot = rule_set.name
    observation.rule_set_version_snapshot = rule_set.version
    observation.save(
        update_fields=[
            "status",
            "analyzed_at",
            "rule_set",
            "rule_set_name_snapshot",
            "rule_set_version_snapshot",
            "updated_at",
        ]
    )

    if status == VitalObservation.Status.CRITICAL:
        doctor_assignments = PatientCareAssignment.objects.filter(
            patient=patient,
            assignment_type=PatientCareAssignment.AssignmentType.DOCTOR,
            ends_at__isnull=True,
        ).select_related("staff__user")
        reason = "; ".join(dict.fromkeys(critical_explanations))[:360]
        for assignment in doctor_assignments:
            notify(
                recipient=assignment.staff.user,
                actor=nurse,
                patient=patient,
                category="CRITICAL_VITALS",
                severity=Notification.Severity.CRITICAL,
                title="Critical vital-sign assessment",
                body=f"{patient.get_full_name()} requires review. {reason}",
                route=f"/doctor/patients/{patient.id}/vitals",
                data={"observation_id": str(observation.id)},
                dedupe_key=f"critical-vitals:{observation.id}:{assignment.staff.user_id}",
            )
    _audit_observation(observation=observation, actor=nurse, request=request)
    return observation


def _audit_observation(*, observation, actor, request=None) -> None:
    record_audit_event(
        actor=actor,
        request=request,
        action="vital_signs.observation.recorded",
        object_type="vital_signs.VitalObservation",
        object_id=observation.id,
        after={
            "patient_id": str(observation.patient_id),
            "status": observation.status,
            "rule_set": observation.rule_set_name_snapshot,
            "rule_set_version": observation.rule_set_version_snapshot,
            "observed_at": observation.observed_at.isoformat(),
        },
    )
