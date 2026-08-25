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
    IcuRecommendation,
    VitalObservation,
    VitalRule,
    VitalRuleEvaluation,
    VitalRuleSet,
    VitalValue,
)
from apps.vital_signs.services.metrics import compute_stability_score


def rule_matches(*, rule: VitalRule, value: Decimal) -> bool:
    value = Decimal(str(value))
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
    assessed_metric_ids: set[object] = set()
    critical_metric_ids: set[object] = set()
    for observed_value in observed_values:
        metric_rules = rules_by_metric[observed_value.metric_id]
        if not metric_rules:
            if observed_value.metric.contributes_to_assessment:
                fully_assessed = False
            continue
        assessed_metric_ids.add(observed_value.metric_id)
        matched_any = False
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
                matched_any = True
                critical_explanations.append(rule.explanation)
        if matched_any:
            critical_metric_ids.add(observed_value.metric_id)

    assessed_count = len(assessed_metric_ids)
    critical_count = len(critical_metric_ids)
    stability_percent, criticality_percent = compute_stability_score(
        assessed_count=assessed_count,
        critical_count=critical_count,
    )

    if critical_explanations:
        status = VitalObservation.Status.CRITICAL
    elif fully_assessed:
        status = VitalObservation.Status.STABLE
    else:
        status = VitalObservation.Status.UNASSESSED
    observation.status = status
    observation.stability_percent = stability_percent
    observation.criticality_percent = criticality_percent
    observation.assessed_metric_count = assessed_count
    observation.critical_metric_count = critical_count
    observation.analyzed_at = analyzed_at
    observation.rule_set = rule_set
    observation.rule_set_name_snapshot = rule_set.name
    observation.rule_set_version_snapshot = rule_set.version
    observation.save(
        update_fields=[
            "status",
            "stability_percent",
            "criticality_percent",
            "assessed_metric_count",
            "critical_metric_count",
            "analyzed_at",
            "rule_set",
            "rule_set_name_snapshot",
            "rule_set_version_snapshot",
            "updated_at",
        ]
    )

    generate_icu_recommendation(observation=observation, patient=patient)

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
            "stability_percent": observation.stability_percent,
            "criticality_percent": observation.criticality_percent,
            "rule_set": observation.rule_set_name_snapshot,
            "rule_set_version": observation.rule_set_version_snapshot,
            "observed_at": observation.observed_at.isoformat(),
        },
    )


def generate_icu_recommendation(*, observation: VitalObservation, patient: Patient) -> IcuRecommendation:
    from apps.hospital.models import Bed

    # 1. Evaluate Specialist presence / absence
    active_episode = patient.care_episodes.filter(status="ACTIVE").first()
    department = active_episode.department if active_episode else None

    specialist_assigned = False
    specialist_overloaded = False
    primary_doctor = None

    # Find primary doctor assignment for this patient
    doctor_assignment = PatientCareAssignment.objects.filter(
        patient=patient,
        assignment_type=PatientCareAssignment.AssignmentType.DOCTOR,
        ends_at__isnull=True,
    ).select_related("staff__user").first()

    if doctor_assignment:
        primary_doctor = doctor_assignment.staff.user
        # Check primary doctor's active assignments load
        active_assignments_count = PatientCareAssignment.objects.filter(
            staff__user=primary_doctor,
            assignment_type=PatientCareAssignment.AssignmentType.DOCTOR,
            ends_at__isnull=True,
        ).count()
        if active_assignments_count > 5:
            specialist_overloaded = True

    # Also check if any doctors are assigned in the active department
    if department:
        department_doctors_count = PatientCareAssignment.objects.filter(
            patient__care_episodes__department=department,
            patient__care_episodes__status="ACTIVE",
            assignment_type=PatientCareAssignment.AssignmentType.DOCTOR,
            ends_at__isnull=True,
        ).values("staff").distinct().count()
        if department_doctors_count > 0:
            specialist_assigned = True
    else:
        # If no department, just fallback to check if primary doctor is assigned
        specialist_assigned = doctor_assignment is not None

    if not specialist_assigned:
        specialist_status = "ABSENT"
        specialist_explanation = "No specialist physician is currently assigned to this department."
    elif specialist_overloaded:
        specialist_status = "OVERLOADED"
        specialist_explanation = f"Primary specialist {primary_doctor.get_full_name()} is overloaded with > 5 active assignments."
    else:
        specialist_status = "AVAILABLE"
        specialist_explanation = "Specialist physician is assigned and available."

    # 2. Evaluate ICU Bed availability
    icu_beds = Bed.objects.filter(room__room_type__icontains="ICU")
    total_icu_beds = icu_beds.count()
    occupied_icu_beds = icu_beds.filter(status=Bed.Status.OCCUPIED).count()

    if total_icu_beds == 0:
        icu_bed_status = "UNAVAILABLE"
        bed_explanation = "No ICU beds are configured in the facility."
    elif occupied_icu_beds >= total_icu_beds:
        icu_bed_status = "OVERLOADED"
        bed_explanation = f"ICU beds are at 100% capacity ({occupied_icu_beds}/{total_icu_beds} occupied)."
    else:
        icu_bed_status = "AVAILABLE"
        bed_explanation = f"ICU beds are available ({total_icu_beds - occupied_icu_beds} of {total_icu_beds} free)."

    # 3. Calculate overall eligibility and score
    eligible = observation.status == VitalObservation.Status.CRITICAL

    # Calculate score
    score = 100
    if specialist_status == "ABSENT":
        score -= 50
    elif specialist_status == "OVERLOADED":
        score -= 25

    if icu_bed_status == "UNAVAILABLE":
        score -= 50
    elif icu_bed_status == "OVERLOADED":
        score -= 30

    score = max(0, score)

    # Explanation text
    explanations = [
        f"ICU Candidacy evaluated: patient status is {observation.status}.",
        specialist_explanation,
        bed_explanation,
    ]
    if eligible:
        if specialist_status in {"ABSENT", "OVERLOADED"} or icu_bed_status in {"UNAVAILABLE", "OVERLOADED"}:
            explanations.append("Local resource constraints detected. Consider initiating external transfer.")
        else:
            explanations.append("Local resources are adequate for immediate ICU admission.")
    explanation_text = " ".join(explanations)

    return IcuRecommendation.objects.create(
        observation=observation,
        eligible=eligible,
        score=score,
        specialist_status=specialist_status,
        icu_bed_status=icu_bed_status,
        explanation=explanation_text,
    )

