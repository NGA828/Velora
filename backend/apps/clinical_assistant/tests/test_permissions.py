import pytest
from django.utils import timezone

from apps.clinical_assistant.permissions import ClinicalAssistantPermission
from apps.identity.models import Invitation, PatientGuardProfile, UserRole
from apps.identity.tests.factories import create_staff, create_user
from apps.patients.models import GuardianAccess, PatientCareAssignment
from apps.vital_signs.tests.test_icu_recommendations import setup_icu_patient


@pytest.mark.django_db
def test_permissions_doctor_and_nurse_access():
    doctor, doc_profile, nurse, patient, metric = setup_icu_patient()

    # Assigned doctor can access
    assert ClinicalAssistantPermission.user_can_access_patient(user=doctor, patient=patient) is True

    # Assigned nurse can access
    assert ClinicalAssistantPermission.user_can_access_patient(user=nurse, patient=patient) is True

    # Unassigned doctor cannot access
    other_doctor, _ = create_staff(
        role=UserRole.DOCTOR, email="other_doc@example.org", employee_number="DOC-OTH-002"
    )
    assert ClinicalAssistantPermission.user_can_access_patient(user=other_doctor, patient=patient) is False

    # Unassigned nurse cannot access
    other_nurse, _ = create_staff(
        role=UserRole.NURSE, email="other_nurse@example.org", employee_number="NUR-OTH-002"
    )
    assert ClinicalAssistantPermission.user_can_access_patient(user=other_nurse, patient=patient) is False


@pytest.mark.django_db
def test_permissions_patient_guard_access():
    doctor, doc_profile, nurse, patient, metric = setup_icu_patient()

    guard_user = create_user(role=UserRole.PATIENT_GUARD, email="guard2@example.org")
    guard_profile = PatientGuardProfile.objects.create(user=guard_user)
    invitation = Invitation.objects.create(
        email="guard2@example.org",
        intended_role=UserRole.PATIENT_GUARD,
        token_hash="token-hash-2",
        invited_by=doctor,
        expires_at=timezone.now() + timezone.timedelta(days=7),
    )
    access = GuardianAccess.objects.create(
        patient=patient,
        guardian=guard_profile,
        invitation=invitation,
        relationship="Parent",
        status=GuardianAccess.Status.ACTIVE,
        granted_by=doctor,
        granted_at=timezone.now(),
    )

    # Active linked guard can access
    assert ClinicalAssistantPermission.user_can_access_patient(user=guard_user, patient=patient) is True

    # If guardian access is revoked, cannot access
    access.status = GuardianAccess.Status.REVOKED
    access.save()
    assert ClinicalAssistantPermission.user_can_access_patient(user=guard_user, patient=patient) is False

    # Unlinked guardian cannot access
    other_guard_user = create_user(role=UserRole.PATIENT_GUARD, email="other_guard@example.org")
    PatientGuardProfile.objects.create(user=other_guard_user)
    assert ClinicalAssistantPermission.user_can_access_patient(user=other_guard_user, patient=patient) is False


@pytest.mark.django_db
def test_permissions_head_of_service_access():
    doctor, doc_profile, nurse, patient, metric = setup_icu_patient()
    head, _ = create_staff(
        role=UserRole.HEAD_OF_SERVICE, email="hos2@example.org", employee_number="HOS-002"
    )
    assert ClinicalAssistantPermission.user_can_access_patient(user=head, patient=patient) is True
