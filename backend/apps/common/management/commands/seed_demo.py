import hashlib
from datetime import date, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.billing.models import ChargeItem, Invoice
from apps.billing.services import add_invoice_line, create_invoice, issue_invoice, record_payment
from apps.clinical_records.models import (
    Allergy,
    ClinicalNote,
    Diagnosis,
    MedicalHistoryEntry,
    TreatmentPlan,
)
from apps.hospital.models import (
    Bed,
    ClinicalCondition,
    Department,
    ExternalHospital,
    ExternalHospitalSpecialty,
    HospitalProfile,
    HospitalServiceAvailability,
    Resource,
    Room,
    ServiceDefinition,
    Specialty,
    SpecialtyCondition,
)
from apps.identity.models import (
    EmploymentStatus,
    Invitation,
    PatientGuardProfile,
    StaffProfile,
    User,
    UserRole,
)
from apps.messaging.services import acknowledge_messages, create_direct_conversation, send_message
from apps.monitoring.models import MonitoringThread
from apps.monitoring.services import add_question, create_thread
from apps.patients.models import GuardianAccess, Patient
from apps.patients.services import register_patient
from apps.prescriptions.models import Medication, Prescription
from apps.prescriptions.services import activate_prescription, create_prescription
from apps.transfers.models import TransferRequest
from apps.transfers.services import (
    create_transfer_request,
    generate_recommendations,
    submit_to_guardian,
)
from apps.vital_signs.models import VitalMetric, VitalObservation
from apps.vital_signs.services import record_and_analyze_observation


class Command(BaseCommand):
    help = "Create idempotent local demonstration data. Never run against production."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="Velora-preview-927!",
            help="Shared local demo password.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo data is disabled when DEBUG is false.")
        password = options["password"]
        hospital, _ = HospitalProfile.objects.get_or_create(
            singleton_key=1,
            defaults={
                "legal_name": "Velora Central Hospital",
                "display_name": "Velora Central Hospital",
                "registration_number": "VCH-CM-001",
                "address": "12 Health Avenue",
                "city": "Yaoundé",
                "region": "Centre",
                "country": "CM",
                "email": "care@velora.local",
                "phone": "+237 600 000 001",
                "timezone": "Africa/Lagos",
            },
        )
        department, _ = Department.objects.get_or_create(
            code="EMR",
            defaults={
                "name": "Emergency Medicine",
                "location": "Ground floor",
                "phone": "+237 600 000 101",
            },
        )
        Department.objects.get_or_create(
            code="PED",
            defaults={"name": "Paediatrics", "location": "First floor"},
        )

        admin, _ = self._staff(
            "admin@velora.local",
            "Amara",
            "Administrator",
            UserRole.ADMIN,
            "ADM-PREVIEW",
            "System Administrator",
            password,
            None,
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.save(update_fields=["is_staff", "is_superuser", "updated_at"])
        self._staff(
            "head@velora.local",
            "Nadia",
            "Essomba",
            UserRole.HEAD_OF_SERVICE,
            "HOS-PREVIEW",
            "Head of Service",
            password,
            department,
        )
        doctor, _ = self._staff(
            "doctor@velora.local",
            "Samuel",
            "Mballa",
            UserRole.DOCTOR,
            "DOC-PREVIEW",
            "Attending Doctor",
            password,
            department,
        )
        nurse, nurse_profile = self._staff(
            "nurse@velora.local",
            "Grace",
            "Fouda",
            UserRole.NURSE,
            "NUR-PREVIEW",
            "Registered Nurse",
            password,
            department,
        )
        accounting, _ = self._staff(
            "accounts@velora.local",
            "Elise",
            "Ngo",
            UserRole.ACCOUNTING,
            "ACC-PREVIEW",
            "Accounting Officer",
            password,
            None,
        )

        specialty, _ = Specialty.objects.get_or_create(
            code="CARD",
            defaults={
                "name": "Cardiology",
                "description": "Cardiovascular specialist capability.",
            },
        )
        condition, _ = ClinicalCondition.objects.get_or_create(
            coding_system="LOCAL",
            code="CV-CARE",
            defaults={
                "name": "Cardiovascular care need",
                "description": "Preview transfer matching label.",
            },
        )
        SpecialtyCondition.objects.get_or_create(
            specialty=specialty,
            condition=condition,
            defaults={"match_weight": Decimal("1.00")},
        )
        service, _ = ServiceDefinition.objects.get_or_create(
            code="ECG",
            defaults={"name": "Electrocardiography", "category": "Diagnostics"},
        )
        HospitalServiceAvailability.objects.get_or_create(service=service, department=department)
        room, _ = Room.objects.get_or_create(
            code="ER-01",
            defaults={
                "department": department,
                "floor": "Ground",
                "room_type": "Observation",
            },
        )
        Bed.objects.get_or_create(room=room, code="A")
        Bed.objects.get_or_create(room=room, code="B")
        Resource.objects.get_or_create(
            asset_code="MON-001",
            defaults={
                "name": "Patient monitor",
                "category": "EQUIPMENT",
                "department": department,
                "quantity_total": 4,
                "quantity_available": 3,
                "status": "AVAILABLE",
            },
        )
        external, _ = ExternalHospital.objects.get_or_create(
            name="Yaoundé Partner Medical Centre",
            defaults={
                "address": "40 Referral Road",
                "city": "Yaoundé",
                "region": "Centre",
                "country": "CM",
                "phone": "+237 600 000 200",
                "email": "contact@partner.local",
                "transfer_email": "transfers@partner.local",
            },
        )
        ExternalHospitalSpecialty.objects.get_or_create(
            external_hospital=external, specialty=specialty
        )
        metric, _ = VitalMetric.objects.get_or_create(
            code="HR_LOCAL",
            defaults={
                "name": "Heart rate",
                "unit": "beats/min",
                "decimal_places": 0,
                "description": "Metric only; no preview threshold is configured.",
            },
        )

        patient = Patient.objects.filter(first_name="Amina", last_name="Biya").first()
        if not patient:
            patient = register_patient(
                doctor=doctor,
                assigned_nurse=nurse_profile,
                department=department,
                patient_data={
                    "first_name": "Amina",
                    "last_name": "Biya",
                    "date_of_birth": date(1992, 8, 17),
                    "sex_at_birth": "FEMALE",
                    "gender_identity": "",
                    "blood_type": "O+",
                    "phone": "+237 600 100 100",
                    "email": "amina@preview.local",
                    "address": "Bastos, Yaoundé",
                    "emergency_contact_name": "Moussa Biya",
                    "emergency_contact_phone": "+237 600 100 101",
                },
                episode_type="INPATIENT",
                admission_reason="Preview care episode for workflow review.",
            )
        episode = patient.care_episodes.filter(status="ACTIVE").first()
        guard = self._guardian(patient, nurse, password)
        guard_access = GuardianAccess.objects.get(
            patient=patient, guardian__user=guard, status="ACTIVE"
        )
        guard_access.can_view_billing = True
        guard_access.save(update_fields=["can_view_billing", "updated_at"])

        Allergy.objects.get_or_create(
            patient=patient,
            substance="Preview allergen",
            status="ACTIVE",
            defaults={
                "reaction": "Preview reaction",
                "severity": "MILD",
                "recorded_at": timezone.now(),
                "recorded_by": nurse,
                "guardian_visibility": "GUARDIAN",
            },
        )
        MedicalHistoryEntry.objects.get_or_create(
            patient=patient,
            title="Preview medical history",
            defaults={
                "category": "MEDICAL",
                "description": "Released preview history entry.",
                "source": "Patient Guard interview",
                "recorded_by": doctor,
                "guardian_visibility": "GUARDIAN",
            },
        )
        Diagnosis.objects.get_or_create(
            patient=patient,
            name_snapshot=condition.name,
            defaults={
                "care_episode": episode,
                "condition": condition,
                "code_snapshot": f"{condition.coding_system}:{condition.code}",
                "description": "Released preview diagnosis context.",
                "status": "PROVISIONAL",
                "diagnosed_at": timezone.now(),
                "diagnosed_by": doctor,
                "guardian_visibility": "GUARDIAN",
            },
        )
        TreatmentPlan.objects.get_or_create(
            patient=patient,
            title="Preview care plan",
            defaults={
                "care_episode": episode,
                "objectives": "Review connected care workflow.",
                "instructions": "Preview instructions only.",
                "status": "ACTIVE",
                "starts_on": timezone.localdate(),
                "authored_by": doctor,
                "guardian_visibility": "GUARDIAN",
            },
        )
        ClinicalNote.objects.get_or_create(
            patient=patient,
            title="Released care update",
            defaults={
                "care_episode": episode,
                "note_type": "PROGRESS",
                "body": "This signed preview note is visible to the authorized Patient Guard.",
                "status": "SIGNED",
                "signed_at": timezone.now(),
                "author": doctor,
                "guardian_visibility": "GUARDIAN",
            },
        )
        if not VitalObservation.objects.filter(patient=patient).exists():
            record_and_analyze_observation(
                patient=patient,
                nurse=nurse,
                observed_at=timezone.now(),
                values=[{"metric": metric, "value": "72"}],
                notes="Preview observation without an approved threshold.",
            )

        medication, _ = Medication.objects.get_or_create(
            generic_name="Preview medication",
            brand_name="",
            form="Tablet",
            strength="10 mg",
            defaults={"description": "Demonstration catalogue entry only."},
        )
        if not Prescription.objects.filter(patient=patient).exists():
            local_now = timezone.now().astimezone(ZoneInfo(hospital.timezone)) - timedelta(
                minutes=5
            )
            prescription = create_prescription(
                doctor=doctor,
                patient=patient,
                starts_on=local_now.date(),
                ends_on=local_now.date() + timedelta(days=1),
                clinical_instructions="Preview workflow only. Not medical advice.",
                items=[
                    {
                        "medication": medication,
                        "dose_amount": Decimal("1"),
                        "dose_unit": "tablet",
                        "route": "ORAL",
                        "frequency_display": "Once daily",
                        "duration_days": 2,
                        "instructions": "Preview administration workflow.",
                        "schedule_type": "SCHEDULED",
                        "prn_max_per_day": None,
                        "schedules": [
                            {
                                "local_time": local_now.time().replace(second=0, microsecond=0),
                                "days_of_week": [],
                            }
                        ],
                    }
                ],
            )
            activate_prescription(prescription=prescription, doctor=doctor)

        if not MonitoringThread.objects.filter(patient=patient).exists():
            thread = create_thread(
                patient=patient,
                doctor=doctor,
                guardian=guard.patient_guard_profile,
                subject="Preview recovery check-in",
            )
            add_question(
                thread=thread,
                doctor=doctor,
                prompt="Has the patient experienced increased pain?",
                response_type="BOOLEAN",
            )
        if not TransferRequest.objects.filter(patient=patient).exists():
            transfer = create_transfer_request(
                patient=patient,
                doctor=doctor,
                guardian=guard.patient_guard_profile,
                reason="Preview specialist referral review",
                clinical_summary="Preview deterministic recommendation summary.",
                urgency="ROUTINE",
                requirements=[
                    {
                        "requirement_type": "SPECIALTY",
                        "specialty": specialty,
                        "weight": Decimal("1.00"),
                        "is_mandatory": True,
                    }
                ],
            )
            recommendations = generate_recommendations(transfer=transfer, doctor=doctor)
            eligible = next(
                (
                    item
                    for item in recommendations
                    if item.eligible and item.external_hospital.transfer_email
                ),
                None,
            )
            if eligible:
                submit_to_guardian(
                    transfer=transfer,
                    hospital=eligible.external_hospital,
                    doctor=doctor,
                )

        conversation = create_direct_conversation(
            creator=doctor,
            participant=guard,
            patient=patient,
            subject="Preview care coordination",
        )
        first = send_message(
            conversation=conversation,
            sender=doctor,
            body="Please review the monitoring question and transfer request.",
            client_message_id="preview-doctor-message",
        )
        acknowledge_messages(
            conversation=conversation,
            recipient=guard,
            up_to_message=first,
            seen=True,
        )
        send_message(
            conversation=conversation,
            sender=guard,
            body="I can see both requests and will review them.",
            client_message_id="preview-guard-message",
        )

        charge, _ = ChargeItem.objects.get_or_create(
            code="ROOM-PREVIEW",
            defaults={
                "name": "Preview room charge",
                "category": "ROOM",
                "default_unit_price": Decimal("100.00"),
                "description": "Demonstration charge only.",
            },
        )
        if not Invoice.objects.filter(patient=patient).exists():
            invoice = create_invoice(
                patient=patient,
                care_episode=episode,
                accounting_user=accounting,
                notes="Preview billing workflow.",
            )
            add_invoice_line(
                invoice=invoice,
                accounting_user=accounting,
                charge_item=charge,
                description="Preview room charge",
                quantity=Decimal("2"),
                unit_price=Decimal("100.00"),
                service_date=timezone.localdate(),
            )
            invoice = issue_invoice(
                invoice=invoice,
                accounting_user=accounting,
                due_at=timezone.now() + timedelta(days=14),
            )
            record_payment(
                invoice=invoice,
                accounting_user=accounting,
                amount=Decimal("50.00"),
                method="MOBILE_MONEY",
                reference="PREVIEW-MM",
                received_at=timezone.now(),
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data ready. Shared password: "
                f"{password}. Users: admin, head, doctor, nurse, guard, accounts @velora.local"
            )
        )

    def _staff(
        self,
        email,
        first_name,
        last_name,
        role,
        employee_number,
        job_title,
        password,
        department,
    ):
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                "must_change_password": False,
            },
        )
        user.first_name = first_name
        user.last_name = last_name
        user.role = role
        user.is_active = True
        user.must_change_password = False
        user.set_password(password)
        user.save()
        profile, _ = StaffProfile.objects.get_or_create(
            user=user,
            defaults={
                "employee_number": employee_number,
                "job_title": job_title,
                "department": department,
            },
        )
        profile.job_title = job_title
        profile.department = department
        profile.employment_status = EmploymentStatus.ACTIVE
        profile.save()
        return user, profile

    def _guardian(self, patient, nurse, password):
        guard, _ = User.objects.get_or_create(
            email="guard@velora.local",
            defaults={
                "first_name": "Moussa",
                "last_name": "Biya",
                "role": UserRole.PATIENT_GUARD,
                "must_change_password": False,
            },
        )
        guard.first_name = "Moussa"
        guard.last_name = "Biya"
        guard.role = UserRole.PATIENT_GUARD
        guard.is_active = True
        guard.must_change_password = False
        guard.set_password(password)
        guard.save()
        profile, _ = PatientGuardProfile.objects.get_or_create(user=guard)
        access = GuardianAccess.objects.filter(patient=patient, guardian=profile).first()
        if not access:
            token_hash = hashlib.sha256(f"preview-guard-{patient.id}".encode()).hexdigest()
            invitation, _ = Invitation.objects.get_or_create(
                token_hash=token_hash,
                defaults={
                    "email": guard.email,
                    "intended_role": UserRole.PATIENT_GUARD,
                    "expires_at": timezone.now(),
                    "accepted_at": timezone.now(),
                    "invited_by": nurse,
                    "context": {"patient_id": str(patient.id)},
                },
            )
            GuardianAccess.objects.create(
                patient=patient,
                guardian=profile,
                invitation=invitation,
                relationship="Sibling",
                status=GuardianAccess.Status.ACTIVE,
                granted_by=nurse,
                granted_at=timezone.now(),
            )
        return guard
