from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.clinical_records.models import (
    Allergy,
    ClinicalNote,
    Diagnosis,
    GuardianVisibility,
    MedicalHistoryEntry,
    TreatmentPlan,
)
from apps.identity.models import UserRole
from apps.patients.models import CareEpisode, Patient
from apps.prescriptions.models import Prescription
from apps.vital_signs.models import VitalObservation


def _calculate_age(date_of_birth) -> int | None:
    if not date_of_birth:
        return None
    today = timezone.localdate()
    return today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))


def build_clinical_context(*, user, patient: Patient) -> dict[str, Any]:
    """
    Constructs a minimal, structured, role-specific clinical context object
    for the DeepSeek Conversational Assistant.

    Strict Role-Based Access Control:
    - DOCTOR / NURSE / HEAD_OF_SERVICE: Full clinical context, rule evaluations,
      exact ICU recommendation snapshot, specialist and bed availability status.
    - PATIENT_GUARD: Strictly guardian-visible records, simplified vitals, plain-language
      ICU summary, zero internal notes, zero internal IDs, zero staff workload details.
    """
    role = user.role if user and getattr(user, "is_authenticated", False) else "ANONYMOUS"
    is_clinical = role in {UserRole.DOCTOR, UserRole.NURSE, UserRole.HEAD_OF_SERVICE}
    is_guard = role == UserRole.PATIENT_GUARD

    # 1. Active Care Episode
    active_episode = patient.care_episodes.filter(status=CareEpisode.Status.ACTIVE).select_related("department").first()

    # 2. Latest Vital Observation & Evaluations
    recent_observations = (
        VitalObservation.objects.filter(patient=patient)
        .select_related("rule_set", "icu_recommendation")
        .prefetch_related("values__metric", "evaluations__rule")
        .order_by("-observed_at", "-created_at")[:5]
    )
    latest_observation = recent_observations[0] if recent_observations else None

    # 3. ICU Recommendation Snapshot (authoritative)
    icu_rec = None
    if latest_observation and hasattr(latest_observation, "icu_recommendation"):
        icu_rec = latest_observation.icu_recommendation
    elif patient.vital_observations.filter(icu_recommendation__isnull=False).exists():
        icu_rec = (
            patient.vital_observations.filter(icu_recommendation__isnull=False)
            .order_by("-observed_at")
            .first()
            .icu_recommendation
        )

    # Build Context
    context: dict[str, Any] = {
        "context_role": role,
        "generated_at": timezone.now().isoformat(),
    }

    age = _calculate_age(patient.date_of_birth)

    if is_guard:
        # Guardian / Patient View
        context["patient"] = {
            "first_name": patient.first_name,
            "medical_record_number": patient.medical_record_number,
            "age": age,
            "sex_at_birth": patient.sex_at_birth,
            "gender_identity": patient.gender_identity,
        }
        context["episode"] = {
            "department": active_episode.department.name if active_episode and active_episode.department else "Inpatient Care",
            "admitted_at": active_episode.admitted_at.isoformat() if active_episode and active_episode.admitted_at else None,
        }

        # Simplified Vitals
        if latest_observation:
            vitals_summary = {}
            for val in latest_observation.values.all():
                vitals_summary[val.metric.name] = f"{val.value} {val.metric.unit}".strip()
            context["latest_vitals"] = {
                "observed_at": latest_observation.observed_at.isoformat(),
                "status": "Critical" if latest_observation.status == VitalObservation.Status.CRITICAL else "Stable",
                "measurements": vitals_summary,
            }
        else:
            context["latest_vitals"] = None

        # Plain-language ICU Recommendation
        if icu_rec:
            context["icu_assessment"] = {
                "eligible": icu_rec.eligible,
                "status": "ICU evaluation recommended by clinical decision support" if icu_rec.eligible else "Standard care observation",
                "explanation": icu_rec.explanation,
                "source": "Velora Clinical Decision Support System",
            }
        else:
            context["icu_assessment"] = None

        # Guardian-visible Diagnoses
        guard_diagnoses = Diagnosis.objects.filter(
            patient=patient,
            guardian_visibility=GuardianVisibility.GUARDIAN,
        ).exclude(status=Diagnosis.Status.ENTERED_IN_ERROR)[:5]
        context["diagnoses"] = [
            {"name": d.name_snapshot, "status": d.status} for d in guard_diagnoses
        ]

        # Guardian-visible Allergies
        guard_allergies = Allergy.objects.filter(
            patient=patient,
            guardian_visibility=GuardianVisibility.GUARDIAN,
            status=Allergy.Status.ACTIVE,
        )
        context["allergies"] = [
            {"substance": a.substance, "severity": a.severity, "reaction": a.reaction}
            for a in guard_allergies
        ]

        # Guardian-visible Treatment Plans
        guard_treatments = TreatmentPlan.objects.filter(
            patient=patient,
            guardian_visibility=GuardianVisibility.GUARDIAN,
            status=TreatmentPlan.Status.ACTIVE,
        )[:3]
        context["active_treatment_plans"] = [
            {"title": t.title, "instructions": t.instructions} for t in guard_treatments
        ]

        # Active Prescriptions (medication names and instructions only)
        active_prescriptions = Prescription.objects.filter(
            patient=patient,
            status=Prescription.Status.ACTIVE,
        ).prefetch_related("items__medication")
        prescriptions_list = []
        for p in active_prescriptions:
            for item in p.items.all():
                prescriptions_list.append(
                    {
                        "medication": item.medication.name,
                        "dose": f"{item.dose_amount} {item.dose_unit}",
                        "frequency": item.frequency_display,
                    }
                )
        context["active_medications"] = prescriptions_list

    else:
        # Doctor / Nurse / Head of Service View
        context["patient"] = {
            "id": str(patient.id),
            "full_name": patient.get_full_name(),
            "medical_record_number": patient.medical_record_number,
            "age": age,
            "sex_at_birth": patient.sex_at_birth,
            "gender_identity": patient.gender_identity,
            "blood_type": getattr(patient, "blood_type", ""),
        }
        context["episode"] = {
            "department": active_episode.department.name if active_episode and active_episode.department else "Unassigned",
            "episode_type": active_episode.episode_type if active_episode else None,
            "admission_reason": active_episode.admission_reason if active_episode else "",
            "admitted_at": active_episode.admitted_at.isoformat() if active_episode and active_episode.admitted_at else None,
        }

        # Detailed Vitals & Evaluations
        if latest_observation:
            vitals_dict = {}
            for val in latest_observation.values.all():
                vitals_dict[val.metric.code or val.metric.name] = {
                    "metric_name": val.metric.name,
                    "value": float(val.value),
                    "unit": val.metric.unit,
                }

            matched_rules = []
            for ev in latest_observation.evaluations.all():
                if ev.matched:
                    matched_rules.append(
                        {
                            "metric": ev.metric_name_snapshot,
                            "rule": ev.rule_name_snapshot,
                            "operator": ev.operator_snapshot,
                            "threshold": f"{ev.lower_value_snapshot or ''} - {ev.upper_value_snapshot or ''}".strip(" -"),
                            "measured_value": float(ev.measured_value),
                            "explanation": ev.explanation,
                        }
                    )

            context["latest_vitals"] = {
                "observation_id": str(latest_observation.id),
                "observed_at": latest_observation.observed_at.isoformat(),
                "status": latest_observation.status,
                "stability_percent": latest_observation.stability_percent,
                "criticality_percent": latest_observation.criticality_percent,
                "rule_set": latest_observation.rule_set_name_snapshot,
                "measurements": vitals_dict,
                "critical_rules_matched": matched_rules,
                "notes": latest_observation.notes,
            }
        else:
            context["latest_vitals"] = None

        # Vital History Trends (Last 5)
        trends = []
        for obs in recent_observations:
            trends.append(
                {
                    "observed_at": obs.observed_at.isoformat(),
                    "status": obs.status,
                    "stability_percent": obs.stability_percent,
                    "criticality_percent": obs.criticality_percent,
                }
            )
        context["vital_trends"] = trends

        # Full Official ICU Recommendation Snapshot
        if icu_rec:
            context["icu_assessment"] = {
                "recommendation_id": str(icu_rec.id),
                "eligible": icu_rec.eligible,
                "readiness_score": icu_rec.score,
                "specialist_status": icu_rec.specialist_status,
                "icu_bed_status": icu_rec.icu_bed_status,
                "official_recommendation": (
                    "Immediate ICU admission recommended (local resources adequate)"
                    if (icu_rec.eligible and icu_rec.score >= 70)
                    else "ICU admission recommended with urgent transfer consideration (resource constraints)"
                    if icu_rec.eligible
                    else "ICU admission not currently indicated"
                ),
                "explanation": icu_rec.explanation,
                "generated_at": icu_rec.generated_at.isoformat(),
                "source": "Velora Deterministic Clinical Decision Support System",
            }
        else:
            context["icu_assessment"] = None

        # Diagnoses (Provisional & Confirmed)
        diagnoses = Diagnosis.objects.filter(patient=patient).exclude(
            status=Diagnosis.Status.ENTERED_IN_ERROR
        )[:10]
        context["diagnoses"] = [
            {
                "code": d.code_snapshot,
                "name": d.name_snapshot,
                "status": d.status,
                "diagnosed_at": d.diagnosed_at.isoformat() if d.diagnosed_at else None,
            }
            for d in diagnoses
        ]

        # Treatment Plans
        treatments = TreatmentPlan.objects.filter(
            patient=patient, status=TreatmentPlan.Status.ACTIVE
        )[:5]
        context["active_treatment_plans"] = [
            {"title": t.title, "objectives": t.objectives, "instructions": t.instructions}
            for t in treatments
        ]

        # Allergies
        allergies = Allergy.objects.filter(patient=patient, status=Allergy.Status.ACTIVE)
        context["allergies"] = [
            {"substance": a.substance, "severity": a.severity, "reaction": a.reaction}
            for a in allergies
        ]

        # Active Prescriptions
        prescriptions = Prescription.objects.filter(
            patient=patient, status=Prescription.Status.ACTIVE
        ).prefetch_related("items__medication")
        rx_list = []
        for rx in prescriptions:
            for item in rx.items.all():
                rx_list.append(
                    {
                        "medication": item.medication.name,
                        "dose": f"{item.dose_amount} {item.dose_unit}",
                        "route": item.route,
                        "frequency": item.frequency_display,
                        "instructions": item.instructions,
                    }
                )
        context["active_prescriptions"] = rx_list

        # Recent Signed Clinical Notes (Doctor / Head of Service only)
        if role in {UserRole.DOCTOR, UserRole.HEAD_OF_SERVICE}:
            notes = ClinicalNote.objects.filter(
                patient=patient, status=ClinicalNote.Status.SIGNED
            ).order_by("-signed_at")[:3]
            context["recent_signed_notes"] = [
                {
                    "title": n.title,
                    "note_type": n.note_type,
                    "body": n.body,
                    "signed_at": n.signed_at.isoformat() if n.signed_at else None,
                }
                for n in notes
            ]

    return context
