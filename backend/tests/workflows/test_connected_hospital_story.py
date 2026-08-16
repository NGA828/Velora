import hashlib
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.hospital.models import (
    Department,
    ExternalHospital,
    ExternalHospitalSpecialty,
    Specialty,
)
from apps.identity.models import Invitation, PatientGuardProfile, UserRole
from apps.identity.tests.factories import create_staff, create_user
from apps.patients.models import GuardianAccess, Patient


def api(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.django_db
def test_connected_hospital_story_across_all_operational_roles():
    head, _ = create_staff(
        role=UserRole.HEAD_OF_SERVICE,
        email="head@example.org",
        employee_number="HOS-001",
    )
    doctor, _ = create_staff(
        role=UserRole.DOCTOR,
        email="doctor@example.org",
        employee_number="DOC-001",
    )
    nurse, nurse_profile = create_staff(
        role=UserRole.NURSE,
        email="nurse@example.org",
        employee_number="NUR-001",
    )
    accounting, _ = create_staff(
        role=UserRole.ACCOUNTING,
        email="accounting@example.org",
        employee_number="ACC-001",
    )
    department = Department.objects.create(code="MED", name="Medicine")
    nurse_profile.department = department
    nurse_profile.save(update_fields=["department", "updated_at"])

    # Doctor intake creates patient, file, episode, and both care assignments atomically.
    registered = api(doctor).post(
        "/api/v1/patients/",
        {
            "first_name": "Connected",
            "last_name": "Patient",
            "date_of_birth": "1990-01-01",
            "sex_at_birth": "NOT_RECORDED",
            "address": "Hospital address",
            "emergency_contact_name": "Responsible Person",
            "emergency_contact_phone": "+237600000000",
            "assigned_nurse": str(nurse_profile.id),
            "department": str(department.id),
            "episode_type": "INPATIENT",
            "admission_reason": "Connected workflow acceptance test",
        },
        format="json",
    )
    assert registered.status_code == 201
    patient = Patient.objects.get(pk=registered.json()["id"])
    assert patient.medical_file.file_number.startswith("MF-VLR-")

    # Nurse-created Guard relationship is represented here as already accepted.
    guard = create_user(role=UserRole.PATIENT_GUARD, email="guard@example.org")
    guard_profile = PatientGuardProfile.objects.create(user=guard)
    invitation = Invitation.objects.create(
        email=guard.email,
        intended_role=UserRole.PATIENT_GUARD,
        token_hash=hashlib.sha256(b"connected-guard").hexdigest(),
        expires_at=timezone.now(),
        accepted_at=timezone.now(),
        invited_by=nurse,
    )
    GuardianAccess.objects.create(
        patient=patient,
        guardian=guard_profile,
        invitation=invitation,
        relationship="Parent",
        status="ACTIVE",
        granted_by=nurse,
        granted_at=timezone.now(),
        can_view_billing=True,
    )

    # Hospital-governed synthetic rule drives a critical observation and Doctor alert.
    metric = (
        api(head)
        .post(
            "/api/v1/vital-metrics/",
            {"code": "WORKFLOW_SCORE", "name": "Workflow score", "unit": "points"},
            format="json",
        )
        .json()
    )
    rule_set = (
        api(head)
        .post(
            "/api/v1/vital-rule-sets/",
            {"name": "Acceptance rules", "version": 1},
            format="json",
        )
        .json()
    )
    api(head).post(
        "/api/v1/vital-rules/",
        {
            "rule_set": rule_set["id"],
            "metric": metric["id"],
            "name": "Synthetic critical workflow rule",
            "operator": "GT",
            "lower_value": "5",
            "priority": 1,
            "explanation": "The hospital-configured acceptance rule matched.",
        },
        format="json",
    )
    assert api(head).post(f"/api/v1/vital-rule-sets/{rule_set['id']}/activate/").status_code == 200
    observation = api(nurse).post(
        "/api/v1/vital-observations/",
        {
            "patient": str(patient.id),
            "values": [{"metric": metric["id"], "value": "8"}],
        },
        format="json",
    )
    assert observation.json()["status"] == "CRITICAL"
    assert api(doctor).get("/api/v1/notifications/?unread=true").json()["pagination"]["count"] >= 1

    # Doctor prescription becomes a concrete Nurse dose and Guard-visible order.
    medication = (
        api(head)
        .post(
            "/api/v1/medications/",
            {
                "generic_name": "Acceptance medicine",
                "brand_name": "",
                "form": "Tablet",
                "strength": "1 unit",
                "is_active": True,
            },
            format="json",
        )
        .json()
    )
    prescription = (
        api(doctor)
        .post(
            "/api/v1/prescriptions/",
            {
                "patient": str(patient.id),
                "starts_on": timezone.localdate().isoformat(),
                "ends_on": timezone.localdate().isoformat(),
                "items": [
                    {
                        "medication": medication["id"],
                        "dose_amount": "1",
                        "dose_unit": "tablet",
                        "route": "ORAL",
                        "frequency_display": "Once",
                        "duration_days": 1,
                        "schedule_type": "SCHEDULED",
                        "schedule_times": [{"local_time": "00:01", "days_of_week": []}],
                    }
                ],
            },
            format="json",
        )
        .json()
    )
    activated = api(doctor).post(f"/api/v1/prescriptions/{prescription['id']}/activate/")
    assert activated.json()["dose_summary"]["PENDING"] == 1
    due = api(nurse).get("/api/v1/medication-doses/due/").json()["data"][0]
    assert (
        api(nurse)
        .post(
            f"/api/v1/medication-doses/{due['id']}/administer/",
            {"notes": "Acceptance administration"},
            format="json",
        )
        .json()["status"]
        == "ADMINISTERED"
    )
    assert api(guard).get("/api/v1/prescriptions/").json()["pagination"]["count"] == 1

    # Doctor and Guard exchange a structured monitoring question and answer.
    thread = (
        api(doctor)
        .post(
            "/api/v1/monitoring-threads/",
            {
                "patient": str(patient.id),
                "guardian": str(guard_profile.id),
                "subject": "Acceptance monitoring",
            },
            format="json",
        )
        .json()
    )
    thread = (
        api(doctor)
        .post(
            f"/api/v1/monitoring-threads/{thread['id']}/questions/",
            {"prompt": "Is the patient comfortable?", "response_type": "BOOLEAN"},
            format="json",
        )
        .json()
    )
    question_id = thread["questions"][0]["id"]
    answered = api(guard).post(
        f"/api/v1/monitoring-threads/{thread['id']}/questions/{question_id}/answer/",
        {"answer": True},
        format="json",
    )
    assert answered.json()["questions"][0]["current_response"]["answer"] is True

    # Deterministic recommendation and Guard approval stay connected to the same patient.
    specialty = Specialty.objects.create(code="ACCEPT", name="Acceptance specialty")
    destination = ExternalHospital.objects.create(
        name="Acceptance Referral Hospital",
        address="Referral road",
        city="Yaoundé",
        country="CM",
        phone="+237611111111",
        transfer_email="transfer@example.org",
    )
    ExternalHospitalSpecialty.objects.create(
        external_hospital=destination,
        specialty=specialty,
    )
    transfer = (
        api(doctor)
        .post(
            "/api/v1/transfer-requests/",
            {
                "patient": str(patient.id),
                "guardian": str(guard_profile.id),
                "reason": "Acceptance transfer",
                "clinical_summary": "Connected summary",
                "urgency": "ROUTINE",
                "requirements": [
                    {
                        "requirement_type": "SPECIALTY",
                        "specialty": str(specialty.id),
                        "weight": "1",
                        "is_mandatory": True,
                    }
                ],
            },
            format="json",
        )
        .json()
    )
    recommended = api(doctor).post(f"/api/v1/transfer-requests/{transfer['id']}/recommend/").json()
    assert recommended["recommendations"][0]["eligible"] is True
    api(doctor).post(
        f"/api/v1/transfer-requests/{transfer['id']}/submit/",
        {"hospital": str(destination.id)},
        format="json",
    )
    decision = api(guard).post(
        f"/api/v1/transfer-requests/{transfer['id']}/decide/",
        {"decision": "APPROVE", "reason": "Accepted"},
        format="json",
    )
    assert decision.json()["status"] == "APPROVED"

    # Real message receipt reaches Seen.
    conversation = (
        api(doctor)
        .post(
            "/api/v1/conversations/",
            {"participant": str(guard.id), "patient": str(patient.id)},
            format="json",
        )
        .json()
    )
    message = (
        api(doctor)
        .post(
            f"/api/v1/conversations/{conversation['id']}/messages/",
            {"body": "Connected workflow message", "client_message_id": str(uuid.uuid4())},
            format="json",
        )
        .json()
    )
    api(guard).post(
        f"/api/v1/conversations/{conversation['id']}/seen/",
        {"up_to_message": message["id"]},
        format="json",
    )
    sender_view = (
        api(doctor).get(f"/api/v1/conversations/{conversation['id']}/messages/").json()["data"][0]
    )
    assert sender_view["delivery_state"] == "SEEN"

    # Accounting receives identity-only access and issues a financial record.
    charge = (
        api(accounting)
        .post(
            "/api/v1/charge-items/",
            {
                "code": "ACCEPT-FEE",
                "name": "Acceptance fee",
                "category": "SERVICE",
                "default_unit_price": "10.00",
                "is_active": True,
            },
            format="json",
        )
        .json()
    )
    invoice = (
        api(accounting)
        .post("/api/v1/invoices/", {"patient": str(patient.id)}, format="json")
        .json()
    )
    api(accounting).post(
        f"/api/v1/invoices/{invoice['id']}/lines/",
        {
            "charge_item": charge["id"],
            "description": "Acceptance fee",
            "quantity": "1",
            "unit_price": "10.00",
            "service_date": timezone.localdate().isoformat(),
        },
        format="json",
    )
    issued = api(accounting).post(
        f"/api/v1/invoices/{invoice['id']}/issue/",
        {"due_at": (timezone.now() + timedelta(days=7)).isoformat()},
        format="json",
    )
    assert issued.json()["status"] == "ISSUED"
    assert api(guard).get("/api/v1/invoices/").json()["pagination"]["count"] == 1
