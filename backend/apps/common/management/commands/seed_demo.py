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
from apps.vital_signs.models import VitalMetric, VitalObservation, VitalRule, VitalRuleSet
from apps.vital_signs.services import (
    activate_rule_set,
    ensure_standard_vital_metrics,
    record_and_analyze_observation,
)


class Command(BaseCommand):
    help = "Create idempotent local demonstration data. Never run against production."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="password123",
            help="Shared local demo password.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo data is disabled when DEBUG is false.")
        password = options["password"]
        self._migrate_legacy_demo_emails()
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
                "email": "care@velora.com",
                "phone": "+237 600 000 001",
                "timezone": "Africa/Lagos",
            },
        )
        if hospital.email != "care@velora.com":
            hospital.email = "care@velora.com"
            hospital.save(update_fields=["email", "updated_at"])
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
            "admin@velora.com",
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
        head, _ = self._staff(
            "head@velora.com",
            "Nadia",
            "Essomba",
            UserRole.HEAD_OF_SERVICE,
            "HOS-PREVIEW",
            "Head of Service",
            password,
            department,
        )
        doctor, _ = self._staff(
            "doctor@velora.com",
            "Samuel",
            "Mballa",
            UserRole.DOCTOR,
            "DOC-PREVIEW",
            "Attending Doctor",
            password,
            department,
        )
        nurse, nurse_profile = self._staff(
            "nurse@velora.com",
            "Grace",
            "Fouda",
            UserRole.NURSE,
            "NUR-PREVIEW",
            "Registered Nurse",
            password,
            department,
        )
        accounting, _ = self._staff(
            "accounts@velora.com",
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
        # Intensive care unit so the ICU decision-support system can evaluate
        # bed capacity (AVAILABLE / OVERLOADED / UNAVAILABLE) in the demo.
        icu_room, _ = Room.objects.get_or_create(
            code="ICU-01",
            defaults={
                "department": department,
                "floor": "First",
                "room_type": "ICU",
            },
        )
        for bed_code in ("ICU-A", "ICU-B", "ICU-C"):
            Bed.objects.get_or_create(room=icu_room, code=bed_code)
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
                "email": "contact@partner.com",
                "transfer_email": "transfers@partner.com",
            },
        )
        if (
            external.email != "contact@partner.com"
            or external.transfer_email != "transfers@partner.com"
        ):
            external.email = "contact@partner.com"
            external.transfer_email = "transfers@partner.com"
            external.save(update_fields=["email", "transfer_email", "updated_at"])
        ExternalHospitalSpecialty.objects.get_or_create(
            external_hospital=external, specialty=specialty
        )
        metrics_by_code = {metric.code: metric for metric in ensure_standard_vital_metrics()}
        VitalMetric.objects.filter(code="HR_LOCAL").update(is_active=False)
        self._ensure_preview_vital_rules(head=head, metrics_by_code=metrics_by_code)

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
                    "email": "amina@preview.com",
                    "address": "Bastos, Yaoundé",
                    "emergency_contact_name": "Moussa Biya",
                    "emergency_contact_phone": "+237 600 100 101",
                },
                episode_type="INPATIENT",
                admission_reason="Preview care episode for workflow review.",
            )
        if patient.email != "amina@preview.com":
            patient.email = "amina@preview.com"
            patient.save(update_fields=["email", "updated_at"])
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
        if not VitalObservation.objects.filter(
            patient=patient, stability_percent__isnull=False
        ).exists():
            preview_values = [
                ("TEMP", "36.8"),
                ("PULSE", "72"),
                ("RR", "16"),
                ("SBP", "118"),
                ("DBP", "76"),
                ("WT", "68.5"),
            ]
            record_and_analyze_observation(
                patient=patient,
                nurse=nurse,
                observed_at=timezone.now(),
                values=[
                    {"metric": metrics_by_code[code], "value": Decimal(value)}
                    for code, value in preview_values
                    if code in metrics_by_code
                ],
                notes="Preview observation of the primary vital signs and body weight.",
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
                f"{password}. Users: admin, head, doctor, nurse, guard, accounts @velora.com"
            )
        )

    def _ensure_preview_vital_rules(self, *, head, metrics_by_code):
        if VitalRuleSet.objects.filter(status=VitalRuleSet.Status.ACTIVE).exists():
            return
        rule_set, created = VitalRuleSet.objects.get_or_create(
            name="Adult vital reference (preview)",
            version=1,
            defaults={
                "description": (
                    "Demonstration adult ranges for the primary vital signs. "
                    "Replace with hospital-approved values before clinical use."
                )
            },
        )
        if rule_set.status != VitalRuleSet.Status.DRAFT:
            return
        preview_rules = (
            (
                "TEMP",
                "Hypothermia",
                VitalRule.Operator.LESS_THAN,
                None,
                "35",
                "Body temperature is below the configured adult lower limit.",
            ),
            (
                "TEMP",
                "Fever",
                VitalRule.Operator.GREATER_THAN,
                "38",
                None,
                "Body temperature is above the configured adult fever threshold.",
            ),
            (
                "PULSE",
                "Bradycardia",
                VitalRule.Operator.LESS_THAN,
                None,
                "60",
                "Pulse is below the configured adult resting range.",
            ),
            (
                "PULSE",
                "Tachycardia",
                VitalRule.Operator.GREATER_THAN,
                "100",
                None,
                "Pulse is above the configured adult resting range.",
            ),
            (
                "RR",
                "Bradypnea",
                VitalRule.Operator.LESS_THAN,
                None,
                "12",
                "Respiration rate is below the configured adult resting range.",
            ),
            (
                "RR",
                "Tachypnea",
                VitalRule.Operator.GREATER_THAN,
                "20",
                None,
                "Respiration rate is above the configured adult resting range.",
            ),
            (
                "SBP",
                "High systolic pressure",
                VitalRule.Operator.GREATER_THAN_OR_EQUAL,
                "130",
                None,
                "Systolic blood pressure meets the configured hypertension threshold.",
            ),
            (
                "DBP",
                "High diastolic pressure",
                VitalRule.Operator.GREATER_THAN_OR_EQUAL,
                "80",
                None,
                "Diastolic blood pressure meets the configured hypertension threshold.",
            ),
        )
        for code, name, operator, lower, upper, explanation in preview_rules:
            metric = metrics_by_code.get(code)
            if metric is None:
                continue
            VitalRule.objects.get_or_create(
                rule_set=rule_set,
                metric=metric,
                name=name,
                defaults={
                    "operator": operator,
                    "lower_value": Decimal(lower) if lower is not None else None,
                    "upper_value": Decimal(upper) if upper is not None else None,
                    "priority": 100,
                    "explanation": explanation,
                    "is_active": True,
                },
            )
        if created or rule_set.rules.filter(is_active=True).exists():
            activate_rule_set(rule_set=rule_set, actor=head)

    def _migrate_legacy_demo_emails(self):
        email_mapping = {
            "admin@velora.local": "admin@velora.com",
            "head@velora.local": "head@velora.com",
            "doctor@velora.local": "doctor@velora.com",
            "nurse@velora.local": "nurse@velora.com",
            "guard@velora.local": "guard@velora.com",
            "accounts@velora.local": "accounts@velora.com",
        }
        for old_email, new_email in email_mapping.items():
            legacy = User.objects.filter(email=old_email).first()
            current = User.objects.filter(email=new_email).first()
            if legacy and not current:
                legacy.email = new_email
                legacy.save(update_fields=["email", "updated_at"])
            elif legacy and current and legacy.pk != current.pk:
                legacy.email = f"legacy-{legacy.id}@example.com"
                legacy.is_active = False
                legacy.save(update_fields=["email", "is_active", "updated_at"])
            Invitation.objects.filter(email=old_email).update(email=new_email)

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
            email="guard@velora.com",
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
