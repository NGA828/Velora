from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.monitoring.models import MonitoringQuestion, MonitoringResponse, MonitoringThread
from apps.notifications.services import notify
from apps.patients.models import GuardianAccess, PatientCareAssignment


def _doctor_assigned(patient, doctor) -> bool:
    return PatientCareAssignment.objects.filter(
        patient=patient,
        staff__user=doctor,
        assignment_type=PatientCareAssignment.AssignmentType.DOCTOR,
        ends_at__isnull=True,
    ).exists()


@transaction.atomic
def create_thread(*, patient, doctor, guardian, subject, request=None):
    if not _doctor_assigned(patient, doctor):
        raise ValidationError("Only an assigned Doctor can monitor this patient.")
    access = GuardianAccess.objects.filter(
        patient=patient,
        guardian=guardian,
        status=GuardianAccess.Status.ACTIVE,
        can_answer_monitoring=True,
    ).first()
    if not access:
        raise ValidationError("Select an active Patient Guard authorized for monitoring.")
    thread = MonitoringThread.objects.create(
        patient=patient,
        doctor=doctor,
        guardian=guardian,
        subject=subject,
        opened_at=timezone.now(),
    )
    record_audit_event(
        actor=doctor,
        request=request,
        action="monitoring.thread.created",
        object_type="monitoring.MonitoringThread",
        object_id=thread.id,
        after={"patient_id": str(patient.id), "guardian_id": str(guardian.id)},
    )
    return thread


@transaction.atomic
def add_question(*, thread, doctor, prompt, response_type, options=None, due_at=None, request=None):
    locked = (
        MonitoringThread.objects.select_for_update()
        .select_related("patient", "guardian__user")
        .get(pk=thread.pk)
    )
    if locked.doctor_id != doctor.id or not _doctor_assigned(locked.patient, doctor):
        raise ValidationError("Only the assigned thread Doctor can add questions.")
    if locked.status != MonitoringThread.Status.OPEN:
        raise ValidationError("Questions cannot be added to a closed monitoring thread.")
    options = options or []
    if response_type == MonitoringQuestion.ResponseType.SINGLE_CHOICE and len(options) < 2:
        raise ValidationError("Single-choice questions require at least two options.")
    if response_type != MonitoringQuestion.ResponseType.SINGLE_CHOICE:
        options = []
    sequence = locked.questions.count() + 1
    question = MonitoringQuestion.objects.create(
        thread=locked,
        prompt=prompt,
        response_type=response_type,
        options=options,
        sequence=sequence,
        asked_at=timezone.now(),
        due_at=due_at,
    )
    notify(
        recipient=locked.guardian.user,
        actor=doctor,
        patient=locked.patient,
        category="MONITORING_QUESTION",
        title="New monitoring question",
        body=f"A new question is available for {locked.patient.get_full_name()}.",
        route="/patient-guard/monitoring",
        dedupe_key=f"monitoring-question:{question.id}",
    )
    record_audit_event(
        actor=doctor,
        request=request,
        action="monitoring.question.created",
        object_type="monitoring.MonitoringQuestion",
        object_id=question.id,
        after={"thread_id": str(locked.id), "response_type": response_type},
    )
    return question


def _validate_answer(question, answer):
    if question.response_type == MonitoringQuestion.ResponseType.BOOLEAN:
        if not isinstance(answer, bool):
            raise ValidationError("Answer this question with Yes or No.")
        return answer
    if question.response_type == MonitoringQuestion.ResponseType.TEXT:
        if not isinstance(answer, str) or not answer.strip():
            raise ValidationError("Enter a text response.")
        return answer.strip()
    if question.response_type == MonitoringQuestion.ResponseType.NUMBER:
        try:
            return str(Decimal(str(answer)))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValidationError("Enter a valid number.") from exc
    if answer not in question.options:
        raise ValidationError("Select one of the configured options.")
    return answer


@transaction.atomic
def answer_question(*, question, guardian, answer, request=None):
    locked = (
        MonitoringQuestion.objects.select_for_update()
        .select_related("thread__patient", "thread__doctor", "thread__guardian")
        .get(pk=question.pk)
    )
    if locked.thread.guardian_id != guardian.id:
        raise ValidationError("This monitoring question is not assigned to you.")
    if locked.thread.status != MonitoringThread.Status.OPEN:
        raise ValidationError("This monitoring thread is closed.")
    if not GuardianAccess.objects.filter(
        patient=locked.thread.patient,
        guardian=guardian,
        status=GuardianAccess.Status.ACTIVE,
        can_answer_monitoring=True,
    ).exists():
        raise ValidationError("Your monitoring response permission is not active.")
    validated_answer = _validate_answer(locked, answer)
    previous = locked.responses.filter(is_current=True).first()
    if previous:
        previous.is_current = False
        previous.save(update_fields=["is_current", "updated_at"])
    response = MonitoringResponse.objects.create(
        question=locked,
        guardian=guardian,
        answer=validated_answer,
        submitted_at=timezone.now(),
        supersedes=previous,
    )
    notify(
        recipient=locked.thread.doctor,
        actor=guardian.user,
        patient=locked.thread.patient,
        category="MONITORING_RESPONSE",
        title="Monitoring response received",
        body=f"A response was submitted for {locked.thread.patient.get_full_name()}.",
        route="/doctor/monitoring",
        dedupe_key=f"monitoring-response:{response.id}",
    )
    record_audit_event(
        actor=guardian.user,
        request=request,
        action="monitoring.response.submitted",
        object_type="monitoring.MonitoringResponse",
        object_id=response.id,
        after={"question_id": str(locked.id), "supersedes": str(previous.id) if previous else None},
    )
    return response


@transaction.atomic
def close_thread(*, thread, doctor, request=None):
    locked = MonitoringThread.objects.select_for_update().get(pk=thread.pk)
    if locked.doctor_id != doctor.id:
        raise ValidationError("Only the thread Doctor can close monitoring.")
    if locked.status != MonitoringThread.Status.OPEN:
        raise ValidationError("This monitoring thread is already closed.")
    locked.status = MonitoringThread.Status.CLOSED
    locked.closed_at = timezone.now()
    locked.save(update_fields=["status", "closed_at", "updated_at"])
    record_audit_event(
        actor=doctor,
        request=request,
        action="monitoring.thread.closed",
        object_type="monitoring.MonitoringThread",
        object_id=locked.id,
    )
    return locked
