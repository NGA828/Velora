import hashlib
import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone

from apps.audit.models import MedicalRecordAccess
from apps.audit.services import record_audit_event, record_medical_access
from apps.clinical_records.models import (
    Allergy,
    Diagnosis,
    MedicalFileAttachment,
    TreatmentPlan,
)
from apps.hospital.models import (
    AvailabilityStatus,
    ExternalHospital,
    SpecialtyCondition,
)
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.patients.models import GuardianAccess, PatientCareAssignment
from apps.prescriptions.models import Prescription
from apps.transfers.models import (
    TransferDecision,
    TransferRecommendation,
    TransferRequest,
    TransferRequirement,
    TransferStatusEvent,
    TransferTransmission,
)
from apps.vital_signs.models import VitalObservation

RECOMMENDATION_RULES_VERSION = "deterministic-v1"


def _doctor_assigned(patient, doctor) -> bool:
    return PatientCareAssignment.objects.filter(
        patient=patient,
        staff__user=doctor,
        assignment_type=PatientCareAssignment.AssignmentType.DOCTOR,
        ends_at__isnull=True,
    ).exists()


def _status_event(request, actor, previous, new, reason=""):
    TransferStatusEvent.objects.create(
        transfer_request=request,
        actor=actor,
        previous_status=previous,
        new_status=new,
        reason=reason,
        occurred_at=timezone.now(),
    )


@transaction.atomic
def create_transfer_request(
    *, patient, doctor, guardian, reason, clinical_summary, urgency, requirements, request=None
):
    if not _doctor_assigned(patient, doctor):
        raise ValidationError("Only an assigned Doctor can request this transfer.")
    access = GuardianAccess.objects.filter(
        patient=patient,
        guardian=guardian,
        status=GuardianAccess.Status.ACTIVE,
        can_decide_transfers=True,
    ).first()
    if not access:
        raise ValidationError("Select an active Patient Guard authorized for transfer decisions.")
    episode = patient.care_episodes.filter(status="ACTIVE").first()
    if not episode:
        raise ValidationError("The patient has no active care episode.")
    if not requirements:
        raise ValidationError("Add at least one transfer requirement.")
    transfer = TransferRequest.objects.create(
        patient=patient,
        care_episode=episode,
        requested_by=doctor,
        decision_guardian=guardian,
        reason=reason,
        clinical_summary=clinical_summary,
        urgency=urgency,
    )
    for data in requirements:
        requirement_type = data["requirement_type"]
        target = data[requirement_type.lower()]
        TransferRequirement.objects.create(
            transfer_request=transfer,
            requirement_type=requirement_type,
            specialty=target
            if requirement_type == TransferRequirement.RequirementType.SPECIALTY
            else None,
            service=target
            if requirement_type == TransferRequirement.RequirementType.SERVICE
            else None,
            condition=target
            if requirement_type == TransferRequirement.RequirementType.CONDITION
            else None,
            label_snapshot=target.name,
            weight=data["weight"],
            is_mandatory=data["is_mandatory"],
        )
    record_audit_event(
        actor=doctor,
        request=request,
        action="transfers.request.created",
        object_type="transfers.TransferRequest",
        object_id=transfer.id,
        after={"patient_id": str(patient.id), "requirements": len(requirements)},
    )
    return transfer


def _requirement_matches(requirement, specialty_ids, service_ids):
    if requirement.requirement_type == TransferRequirement.RequirementType.SPECIALTY:
        return requirement.specialty_id in specialty_ids
    if requirement.requirement_type == TransferRequirement.RequirementType.SERVICE:
        return requirement.service_id in service_ids
    mapped_specialties = set(
        SpecialtyCondition.objects.filter(condition_id=requirement.condition_id).values_list(
            "specialty_id", flat=True
        )
    )
    return bool(mapped_specialties & specialty_ids)


@transaction.atomic
def generate_recommendations(*, transfer, doctor, request=None):
    locked = TransferRequest.objects.select_for_update().get(pk=transfer.pk)
    if not _doctor_assigned(locked.patient, doctor):
        raise ValidationError("Only an assigned Doctor can generate recommendations.")
    if locked.status not in {TransferRequest.Status.DRAFT, TransferRequest.Status.RECOMMENDED}:
        raise ValidationError("Recommendations cannot be changed after Guard submission.")
    requirements = list(locked.requirements.select_related("specialty", "service", "condition"))
    if not requirements:
        raise ValidationError("Add at least one transfer requirement.")
    generation = locked.recommendation_generation + 1
    generated_at = timezone.now()
    candidates = []
    hospitals = ExternalHospital.objects.filter(is_active=True).prefetch_related(
        "specialty_capabilities", "service_capabilities"
    )
    total_weight = sum((item.weight for item in requirements), Decimal("0"))
    for hospital in hospitals:
        specialty_ids = {
            item.specialty_id
            for item in hospital.specialty_capabilities.all()
            if item.availability_status != AvailabilityStatus.UNAVAILABLE
        }
        service_ids = {
            item.service_id
            for item in hospital.service_capabilities.all()
            if item.availability_status != AvailabilityStatus.UNAVAILABLE
        }
        matched = []
        missing = []
        matched_weight = Decimal("0")
        eligible = True
        for requirement in requirements:
            is_match = _requirement_matches(requirement, specialty_ids, service_ids)
            snapshot = {
                "type": requirement.requirement_type,
                "label": requirement.label_snapshot,
                "weight": str(requirement.weight),
                "mandatory": requirement.is_mandatory,
            }
            if is_match:
                matched.append(snapshot)
                matched_weight += requirement.weight
            else:
                missing.append(snapshot)
                if requirement.is_mandatory:
                    eligible = False
        score = (
            (matched_weight / total_weight * Decimal("100")).quantize(Decimal("0.01"))
            if total_weight
            else Decimal("0")
        )
        eligibility_text = (
            "All mandatory requirements matched."
            if eligible
            else "One or more mandatory requirements are missing."
        )
        explanation = (
            f"Matched {len(matched)} of {len(requirements)} configured requirements. "
            f"{eligibility_text}"
        )
        candidates.append(
            {
                "hospital": hospital,
                "eligible": eligible,
                "score": score,
                "matched": matched,
                "missing": missing,
                "explanation": explanation,
            }
        )
    candidates.sort(
        key=lambda item: (
            not item["eligible"],
            -item["score"],
            item["hospital"].name.lower(),
        )
    )
    recommendations = []
    for rank, item in enumerate(candidates, start=1):
        recommendations.append(
            TransferRecommendation.objects.create(
                transfer_request=locked,
                external_hospital=item["hospital"],
                generation=generation,
                eligible=item["eligible"],
                score=item["score"],
                rank=rank,
                matched_requirements=item["matched"],
                missing_requirements=item["missing"],
                explanation=item["explanation"],
                generated_at=generated_at,
                rules_version=RECOMMENDATION_RULES_VERSION,
            )
        )
    previous = locked.status
    locked.status = TransferRequest.Status.RECOMMENDED
    locked.recommendation_generation = generation
    locked.save(update_fields=["status", "recommendation_generation", "updated_at"])
    if previous != locked.status:
        _status_event(locked, doctor, previous, locked.status)
    record_audit_event(
        actor=doctor,
        request=request,
        action="transfers.recommendations.generated",
        object_type="transfers.TransferRequest",
        object_id=locked.id,
        after={"generation": generation, "candidate_count": len(recommendations)},
    )
    return recommendations


@transaction.atomic
def submit_to_guardian(*, transfer, hospital, doctor, request=None):
    locked = (
        TransferRequest.objects.select_for_update()
        .select_related("patient", "decision_guardian__user")
        .get(pk=transfer.pk)
    )
    if not _doctor_assigned(locked.patient, doctor):
        raise ValidationError("Only an assigned Doctor can submit this transfer.")
    if locked.status != TransferRequest.Status.RECOMMENDED:
        raise ValidationError("Generate recommendations before Guard submission.")
    recommendation = locked.recommendations.filter(
        generation=locked.recommendation_generation,
        external_hospital=hospital,
        eligible=True,
    ).first()
    if not recommendation:
        raise ValidationError("Select an eligible hospital from the latest recommendations.")
    if not hospital.transfer_email:
        raise ValidationError("The selected hospital has no medical transfer email.")
    previous = locked.status
    locked.selected_hospital = hospital
    locked.status = TransferRequest.Status.PENDING_GUARDIAN
    locked.submitted_at = timezone.now()
    locked.save(update_fields=["selected_hospital", "status", "submitted_at", "updated_at"])
    _status_event(locked, doctor, previous, locked.status)
    notify(
        recipient=locked.decision_guardian.user,
        actor=doctor,
        patient=locked.patient,
        category="TRANSFER_DECISION_REQUIRED",
        severity=Notification.Severity.WARNING,
        title="Transfer decision required",
        body=f"Review the proposed transfer for {locked.patient.get_full_name()}.",
        route="/patient-guard/transfers",
        dedupe_key=f"transfer-decision:{locked.id}",
    )
    return locked


@transaction.atomic
def decide_transfer(*, transfer, guardian, decision, reason="", request=None):
    locked = (
        TransferRequest.objects.select_for_update()
        .select_related("patient", "requested_by")
        .get(pk=transfer.pk)
    )
    if locked.decision_guardian_id != guardian.id:
        raise ValidationError("This transfer decision is not assigned to you.")
    if locked.status != TransferRequest.Status.PENDING_GUARDIAN:
        raise ValidationError("This transfer is not awaiting a decision.")
    if decision == TransferDecision.Decision.REJECT and not reason.strip():
        raise ValidationError("A reason is required when rejecting a transfer.")
    if not GuardianAccess.objects.filter(
        patient=locked.patient,
        guardian=guardian,
        status=GuardianAccess.Status.ACTIVE,
        can_decide_transfers=True,
    ).exists():
        raise ValidationError("Your transfer decision permission is not active.")
    decided_at = timezone.now()
    TransferDecision.objects.create(
        transfer_request=locked,
        guardian=guardian,
        decision=decision,
        reason=reason,
        decided_at=decided_at,
    )
    previous = locked.status
    locked.status = (
        TransferRequest.Status.APPROVED
        if decision == TransferDecision.Decision.APPROVE
        else TransferRequest.Status.REJECTED
    )
    locked.decided_at = decided_at
    locked.save(update_fields=["status", "decided_at", "updated_at"])
    _status_event(locked, guardian.user, previous, locked.status, reason)
    notify(
        recipient=locked.requested_by,
        actor=guardian.user,
        patient=locked.patient,
        category="TRANSFER_DECISION_RECEIVED",
        severity=(
            Notification.Severity.SUCCESS
            if decision == TransferDecision.Decision.APPROVE
            else Notification.Severity.WARNING
        ),
        title=f"Transfer {locked.status.lower()}",
        body=(
            f"The Patient Guard {locked.status.lower()} the transfer for "
            f"{locked.patient.get_full_name()}."
        ),
        route="/doctor/transfers",
        dedupe_key=f"transfer-decision-result:{locked.id}",
    )
    return locked


def _medical_package(transfer):
    patient = transfer.patient
    latest_vitals = VitalObservation.objects.filter(patient=patient).prefetch_related(
        "values__metric"
    )[:5]
    return {
        "generated_at": timezone.now(),
        "transfer_request_id": str(transfer.id),
        "destination": transfer.selected_hospital.name,
        "patient": {
            "medical_record_number": patient.medical_record_number,
            "full_name": patient.get_full_name(),
            "date_of_birth": patient.date_of_birth,
            "sex_at_birth": patient.sex_at_birth,
            "blood_type": patient.blood_type,
        },
        "transfer": {
            "reason": transfer.reason,
            "clinical_summary": transfer.clinical_summary,
            "urgency": transfer.urgency,
        },
        "allergies": list(
            Allergy.objects.filter(patient=patient, status="ACTIVE").values(
                "substance", "reaction", "severity"
            )
        ),
        "diagnoses": list(
            Diagnosis.objects.filter(patient=patient)
            .exclude(status="ENTERED_IN_ERROR")
            .values("code_snapshot", "name_snapshot", "description", "status", "diagnosed_at")
        ),
        "treatment_plans": list(
            TreatmentPlan.objects.filter(patient=patient, status="ACTIVE").values(
                "title", "objectives", "instructions", "starts_on", "ends_on"
            )
        ),
        "attachments": list(
            MedicalFileAttachment.objects.filter(patient=patient).values(
                "original_name", "mime_type", "byte_size", "checksum", "uploaded_at"
            )
        ),
        "active_prescriptions": [
            {
                "starts_on": item.starts_on,
                "ends_on": item.ends_on,
                "items": [
                    {
                        "medication": prescribed.medication.generic_name,
                        "strength": prescribed.medication.strength,
                        "dose": f"{prescribed.dose_amount} {prescribed.dose_unit}",
                        "route": prescribed.route,
                        "frequency": prescribed.frequency_display,
                        "instructions": prescribed.instructions,
                    }
                    for prescribed in item.items.select_related("medication")
                ],
            }
            for item in Prescription.objects.filter(patient=patient, status="ACTIVE")
        ],
        "recent_vitals": [
            {
                "observed_at": observation.observed_at,
                "status": observation.status,
                "values": [
                    {
                        "metric": value.metric.name,
                        "value": str(value.value),
                        "unit": value.metric.unit,
                    }
                    for value in observation.values.all()
                ],
            }
            for observation in latest_vitals
        ],
    }


def transmit_medical_package(*, transfer, doctor, request=None):
    with transaction.atomic():
        locked = (
            TransferRequest.objects.select_for_update()
            .select_related("patient", "selected_hospital")
            .get(pk=transfer.pk)
        )
        if not _doctor_assigned(locked.patient, doctor):
            raise ValidationError("Only an assigned Doctor can transmit the medical package.")
        if locked.status != TransferRequest.Status.APPROVED:
            raise ValidationError("The Patient Guard must approve before transmission.")
        if not locked.selected_hospital or not locked.selected_hospital.transfer_email:
            raise ValidationError("The selected hospital has no transfer email.")
        package = _medical_package(locked)
        content = json.dumps(package, cls=DjangoJSONEncoder, indent=2).encode("utf-8")
        checksum = hashlib.sha256(content).hexdigest()
        relative = (
            Path("transfer_packages") / str(locked.id) / f"medical-package-{checksum[:12]}.json"
        )
        absolute = Path(settings.MEDIA_ROOT) / relative
        absolute.parent.mkdir(parents=True, exist_ok=True)
        absolute.write_bytes(content)
        transmission = TransferTransmission.objects.create(
            transfer_request=locked,
            external_hospital=locked.selected_hospital,
            initiated_by=doctor,
            recipient_email=locked.selected_hospital.transfer_email,
            package_storage_key=str(relative),
            checksum=checksum,
        )
    try:
        message = EmailMessage(
            subject=f"Authorized patient transfer package — {locked.patient.medical_record_number}",
            body=(
                "An authorized medical transfer package is attached. "
                "Please handle it according to your clinical privacy procedures."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[transmission.recipient_email],
        )
        message.attach(absolute.name, content, "application/json")
        # Include every document attached to the patient's medical file so the
        # destination hospital receives the complete record.
        for attachment in MedicalFileAttachment.objects.filter(patient=locked.patient):
            try:
                message.attach(
                    attachment.original_name,
                    attachment.file.read(),
                    attachment.mime_type,
                )
            except Exception:
                # An unreadable attachment must not block the authorized
                # package; the JSON payload lists its metadata.
                continue
        message.send(fail_silently=False)
    except Exception as exc:
        transmission.status = TransferTransmission.Status.FAILED
        transmission.attempts += 1
        transmission.last_error = str(exc)[:500]
        transmission.save(update_fields=["status", "attempts", "last_error", "updated_at"])
        raise ValidationError(
            "The medical package was prepared but email delivery failed. Retry after checking SMTP."
        ) from exc

    with transaction.atomic():
        locked = TransferRequest.objects.select_for_update().get(pk=locked.pk)
        now = timezone.now()
        transmission.status = TransferTransmission.Status.SENT
        transmission.attempts += 1
        transmission.sent_at = now
        transmission.last_error = ""
        transmission.save(
            update_fields=["status", "attempts", "sent_at", "last_error", "updated_at"]
        )
        previous = locked.status
        locked.status = TransferRequest.Status.FILE_SENT
        locked.transmitted_at = now
        locked.save(update_fields=["status", "transmitted_at", "updated_at"])
        _status_event(locked, doctor, previous, locked.status)
        record_medical_access(
            user=doctor,
            patient=locked.patient,
            object_type="transfers.TransferTransmission",
            object_id=transmission.id,
            action=MedicalRecordAccess.Action.TRANSMIT,
            purpose="Approved external hospital transfer",
            request=request,
        )
        record_audit_event(
            actor=doctor,
            request=request,
            action="transfers.medical_package.sent",
            object_type="transfers.TransferTransmission",
            object_id=transmission.id,
            after={"recipient": transmission.recipient_email, "checksum": checksum},
        )
    return transmission


def suggest_transfer_requirements(*, patient) -> list[dict]:
    """Derive transfer-requirement suggestions from the patient's medical file:
    every active (non-resolved, non-error) diagnosis contributes its clinical
    condition as a CONDITION requirement, and each condition's mapped
    specialties (the Head of Service's specialty→condition catalogue) as
    SPECIALTY requirements. De-duplicated, with weights from the catalogue."""
    diagnoses = (
        Diagnosis.objects.filter(patient=patient)
        .exclude(status=Diagnosis.Status.ENTERED_IN_ERROR)
        .exclude(status=Diagnosis.Status.RESOLVED)
        .filter(condition__isnull=False)
        .select_related("condition")
    )
    suggestions: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(requirement_type: str, target_id, label: str, weight: str, source: str) -> None:
        key = (requirement_type, str(target_id))
        if key in seen:
            return
        seen.add(key)
        suggestions.append(
            {
                "requirement_type": requirement_type,
                "target": str(target_id),
                "label": label,
                "weight": weight,
                "is_mandatory": False,
                "source": source,
            }
        )

    for diagnosis in diagnoses:
        condition = diagnosis.condition
        add(
            "CONDITION",
            condition.id,
            condition.name,
            "1.00",
            f"From diagnosis: {diagnosis.name_snapshot}",
        )
        mappings = SpecialtyCondition.objects.filter(
            condition=condition, specialty__is_active=True
        ).select_related("specialty")
        for mapping in mappings:
            add(
                "SPECIALTY",
                mapping.specialty_id,
                mapping.specialty.name,
                str(mapping.match_weight),
                f"From condition: {condition.name}",
            )
    return suggestions
