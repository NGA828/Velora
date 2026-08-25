from decimal import Decimal
import pytest
from django.utils import timezone

from apps.clinical_records.models import Allergy, ClinicalNote, Diagnosis, GuardianVisibility, TreatmentPlan
from apps.identity.models import PatientGuardProfile, UserRole
from apps.identity.tests.factories import create_staff, create_user
from apps.patients.models import GuardianAccess
from apps.vital_signs.models import IcuRecommendation, VitalObservation, VitalRule, VitalRuleSet
from apps.vital_signs.services import activate_rule_set
from apps.vital_signs.tests.test_icu_recommendations import setup_icu_patient
from apps.clinical_assistant.services.context_builder import build_clinical_context
from apps.identity.models import Invitation


@pytest.mark.django_db
def test_context_builder_for_doctor():
    doctor, doc_profile, nurse, patient, metric = setup_icu_patient()

    # Add diagnosis, treatment, allergy, note
    diag = Diagnosis.objects.create(
        patient=patient,
        code_snapshot="J18.9",
        name_snapshot="Pneumonia, unspecified organism",
        status=Diagnosis.Status.CONFIRMED,
        diagnosed_at=timezone.now(),
        diagnosed_by=doctor,
        guardian_visibility=GuardianVisibility.GUARDIAN,
    )
    allergy = Allergy.objects.create(
        patient=patient,
        substance="Penicillin",
        severity=Allergy.Severity.SEVERE,
        reaction="Anaphylaxis",
        status=Allergy.Status.ACTIVE,
        recorded_at=timezone.now(),
        recorded_by=doctor,
        guardian_visibility=GuardianVisibility.GUARDIAN,
    )
    treatment = TreatmentPlan.objects.create(
        patient=patient,
        title="IV Antibiotic Regimen",
        instructions="Administer Ceftriaxone 1g IV daily",
        status=TreatmentPlan.Status.ACTIVE,
        starts_on=timezone.now().date(),
        authored_by=doctor,
        guardian_visibility=GuardianVisibility.GUARDIAN,
    )
    note = ClinicalNote.objects.create(
        patient=patient,
        author=doctor,
        title="Daily Progress Note",
        note_type=ClinicalNote.NoteType.PROGRESS,
        body="Patient respiratory status worsening. Initiate ICU escalation evaluation.",
        status=ClinicalNote.Status.SIGNED,
        signed_at=timezone.now(),
    )

    # Record vital observation that triggers critical ICU recommendation
    from apps.vital_signs.services import record_and_analyze_observation
    obs = record_and_analyze_observation(
        patient=patient,
        nurse=nurse,
        observed_at=timezone.now(),
        values=[{"metric": metric, "value": Decimal("39.2")}],
    )

    context = build_clinical_context(user=doctor, patient=patient)

    assert context["context_role"] == UserRole.DOCTOR
    assert context["patient"]["full_name"] == patient.get_full_name()
    assert context["patient"]["medical_record_number"] == patient.medical_record_number
    assert context["latest_vitals"] is not None
    assert context["latest_vitals"]["status"] == VitalObservation.Status.CRITICAL
    assert len(context["latest_vitals"]["critical_rules_matched"]) >= 1

    # Official ICU recommendation snapshot is present
    assert context["icu_assessment"] is not None
    assert context["icu_assessment"]["eligible"] is True
    assert "High fever detected" in context["latest_vitals"]["critical_rules_matched"][0]["explanation"]
    assert context["icu_assessment"]["source"] == "Velora Deterministic Clinical Decision Support System"

    # Diagnoses, allergies, treatments, notes are present
    assert len(context["diagnoses"]) >= 1
    assert context["diagnoses"][0]["name"] == "Pneumonia, unspecified organism"
    assert len(context["allergies"]) >= 1
    assert context["allergies"][0]["substance"] == "Penicillin"
    assert len(context["active_treatment_plans"]) >= 1
    assert len(context["recent_signed_notes"]) >= 1


@pytest.mark.django_db
def test_context_builder_for_patient_guard_strict_visibility():
    doctor, doc_profile, nurse, patient, metric = setup_icu_patient()

    # Create Guardian user & profile
    guard_user = create_user(role=UserRole.PATIENT_GUARD, email="guard@example.org")
    guard_profile = PatientGuardProfile.objects.create(user=guard_user)
    invitation = Invitation.objects.create(
        email="guard@example.org",
        intended_role=UserRole.PATIENT_GUARD,
        token_hash="token-hash-1",
        invited_by=doctor,
        expires_at=timezone.now() + timezone.timedelta(days=7),
    )
    GuardianAccess.objects.create(
        patient=patient,
        guardian=guard_profile,
        invitation=invitation,
        relationship="Spouse",
        status=GuardianAccess.Status.ACTIVE,
        can_view_medical_file=True,
        granted_by=doctor,
        granted_at=timezone.now(),
    )

    # Create one GUARDIAN-visible diagnosis and one INTERNAL diagnosis
    Diagnosis.objects.create(
        patient=patient,
        code_snapshot="J18.9",
        name_snapshot="Pneumonia (Guardian Visible)",
        status=Diagnosis.Status.CONFIRMED,
        diagnosed_at=timezone.now(),
        diagnosed_by=doctor,
        guardian_visibility=GuardianVisibility.GUARDIAN,
    )
    Diagnosis.objects.create(
        patient=patient,
        code_snapshot="Z99.9",
        name_snapshot="Confidential Internal Finding",
        status=Diagnosis.Status.CONFIRMED,
        diagnosed_at=timezone.now(),
        diagnosed_by=doctor,
        guardian_visibility=GuardianVisibility.INTERNAL,
    )

    # Create an internal clinical note (should NEVER be exposed to guard)
    ClinicalNote.objects.create(
        patient=patient,
        author=doctor,
        title="Internal Staff Assessment",
        note_type=ClinicalNote.NoteType.PROGRESS,
        body="Confidential staff discussion.",
        status=ClinicalNote.Status.SIGNED,
        signed_at=timezone.now(),
    )

    context = build_clinical_context(user=guard_user, patient=patient)

    assert context["context_role"] == UserRole.PATIENT_GUARD
    # Guard context must NOT contain internal clinical notes
    assert "recent_signed_notes" not in context
    # Guard context must only contain guardian-visible diagnoses
    assert len(context["diagnoses"]) == 1
    assert context["diagnoses"][0]["name"] == "Pneumonia (Guardian Visible)"
    # Guard context does not expose internal doctor overload stats
    assert "specialist_status" not in (context.get("icu_assessment") or {})
