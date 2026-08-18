from django.db.models import Count, OuterRef, Prefetch, Q, Subquery

from apps.identity.models import UserRole
from apps.patients.models import CareEpisode, GuardianAccess, Patient, PatientCareAssignment


def patients_visible_to(user):
    from apps.vital_signs.models import VitalObservation

    latest_vitals = VitalObservation.objects.filter(patient=OuterRef("pk")).order_by(
        "-observed_at", "-created_at"
    )
    queryset = Patient.objects.select_related("medical_file").annotate(
        active_guardian_count=Count(
            "guardian_accesses",
            filter=Q(guardian_accesses__status=GuardianAccess.Status.ACTIVE),
            distinct=True,
        ),
        latest_vital_status=Subquery(latest_vitals.values("status")[:1]),
        latest_vital_at=Subquery(latest_vitals.values("observed_at")[:1]),
        latest_vital_stability_percent=Subquery(latest_vitals.values("stability_percent")[:1]),
        latest_vital_criticality_percent=Subquery(latest_vitals.values("criticality_percent")[:1]),
        latest_vital_assessed_metric_count=Subquery(
            latest_vitals.values("assessed_metric_count")[:1]
        ),
        latest_vital_critical_metric_count=Subquery(
            latest_vitals.values("critical_metric_count")[:1]
        ),
    )
    if user.role in {UserRole.DOCTOR, UserRole.NURSE}:
        queryset = queryset.filter(
            care_assignments__staff__user=user,
            care_assignments__assignment_type=user.role,
            care_assignments__ends_at__isnull=True,
        )
    elif user.role == UserRole.PATIENT_GUARD:
        queryset = queryset.filter(
            guardian_accesses__guardian__user=user,
            guardian_accesses__status=GuardianAccess.Status.ACTIVE,
        )
    else:
        return queryset.none()

    active_assignments = PatientCareAssignment.objects.filter(ends_at__isnull=True).select_related(
        "staff__user", "care_episode"
    )
    active_episodes = CareEpisode.objects.filter(status=CareEpisode.Status.ACTIVE).select_related(
        "department"
    )
    return queryset.distinct().prefetch_related(
        Prefetch("care_assignments", queryset=active_assignments, to_attr="active_assignments"),
        Prefetch("care_episodes", queryset=active_episodes, to_attr="active_episodes"),
    )


def user_has_active_assignment(*, user, patient: Patient, assignment_type: str) -> bool:
    return PatientCareAssignment.objects.filter(
        patient=patient,
        staff__user=user,
        assignment_type=assignment_type,
        ends_at__isnull=True,
    ).exists()
