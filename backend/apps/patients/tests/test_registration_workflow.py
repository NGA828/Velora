import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.clinical_records.models import MedicalFile
from apps.hospital.models import Department
from apps.identity.models import UserRole
from apps.identity.tests.factories import create_staff
from apps.notifications.models import Notification
from apps.patients.models import CareEpisode, Patient, PatientCareAssignment


def registration_payload(nurse_id, department_id):
    return {
        "first_name": "Mireille",
        "last_name": "Nkoa",
        "date_of_birth": "1988-05-14",
        "sex_at_birth": "FEMALE",
        "gender_identity": "",
        "blood_type": "O+",
        "phone": "+237600100100",
        "email": "mireille@example.org",
        "address": "Bastos, Yaoundé",
        "emergency_contact_name": "Jean Nkoa",
        "emergency_contact_phone": "+237600100101",
        "assigned_nurse": str(nurse_id),
        "department": str(department_id),
        "episode_type": "INPATIENT",
        "admission_reason": "Hospital-approved intake reason",
    }


@pytest.mark.django_db
def test_doctor_registration_creates_connected_record_and_nurse_assignment():
    department = Department.objects.create(code="MED", name="Medicine")
    doctor, doctor_profile = create_staff(
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

    assert response.status_code == 201
    patient = Patient.objects.get()
    assert patient.medical_record_number.startswith("VLR-")
    assert patient.status == Patient.Status.ADMITTED
    assert MedicalFile.objects.filter(patient=patient).exists()
    assert CareEpisode.objects.filter(patient=patient, status="ACTIVE").exists()
    assert PatientCareAssignment.objects.filter(
        patient=patient,
        staff=doctor_profile,
        assignment_type="DOCTOR",
        ends_at__isnull=True,
    ).exists()
    assert PatientCareAssignment.objects.filter(
        patient=patient,
        staff=nurse_profile,
        assignment_type="NURSE",
        ends_at__isnull=True,
    ).exists()
    assert Notification.objects.filter(
        recipient=nurse, category="PATIENT_ASSIGNED", patient=patient
    ).exists()

    client.force_authenticate(nurse)
    nurse_list = client.get(reverse("patients:patient-list"))
    dashboard = client.get(reverse("patients:patient-dashboard"))
    assert nurse_list.status_code == 200
    assert nurse_list.json()["data"][0]["id"] == str(patient.id)
    assert dashboard.status_code == 200
    assert dashboard.json()["total_assigned"] == 1
    assert dashboard.json()["without_guard"] == 1


@pytest.mark.django_db
def test_unassigned_staff_cannot_guess_patient_id():
    department = Department.objects.create(code="MED", name="Medicine")
    doctor, _ = create_staff(
        role=UserRole.DOCTOR, email="doctor@example.org", employee_number="DOC-001"
    )
    assigned_nurse, assigned_profile = create_staff(
        role=UserRole.NURSE, email="assigned@example.org", employee_number="NUR-001"
    )
    unrelated_nurse, _ = create_staff(
        role=UserRole.NURSE, email="unrelated@example.org", employee_number="NUR-002"
    )
    client = APIClient()
    client.force_authenticate(doctor)
    created = client.post(
        reverse("patients:patient-list"),
        registration_payload(assigned_profile.id, department.id),
        format="json",
    )
    patient_id = created.json()["id"]

    client.force_authenticate(unrelated_nurse)
    detail = client.get(reverse("patients:patient-detail", kwargs={"pk": patient_id}))
    listing = client.get(reverse("patients:patient-list"))

    assert detail.status_code == 404
    assert listing.json()["pagination"]["count"] == 0
    assert assigned_nurse.id != unrelated_nurse.id


@pytest.mark.django_db
def test_duplicate_current_patient_is_rejected_without_partial_records():
    department = Department.objects.create(code="MED", name="Medicine")
    doctor, _ = create_staff(
        role=UserRole.DOCTOR, email="doctor@example.org", employee_number="DOC-001"
    )
    _, nurse_profile = create_staff(
        role=UserRole.NURSE, email="nurse@example.org", employee_number="NUR-001"
    )
    client = APIClient()
    client.force_authenticate(doctor)
    payload = registration_payload(nurse_profile.id, department.id)

    assert client.post(reverse("patients:patient-list"), payload, format="json").status_code == 201
    duplicate = client.post(reverse("patients:patient-list"), payload, format="json")

    assert duplicate.status_code == 400
    assert Patient.objects.count() == 1
    assert MedicalFile.objects.count() == 1
    assert CareEpisode.objects.count() == 1
