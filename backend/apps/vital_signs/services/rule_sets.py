from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.vital_signs.models import VitalRuleSet


@transaction.atomic
def activate_rule_set(*, rule_set: VitalRuleSet, actor, request=None) -> VitalRuleSet:
    locked = VitalRuleSet.objects.select_for_update().get(pk=rule_set.pk)
    if locked.status != VitalRuleSet.Status.DRAFT:
        raise ValidationError("Only a draft rule set can be activated.")
    if not locked.rules.filter(is_active=True, metric__is_active=True).exists():
        raise ValidationError("Add at least one active rule with an active metric first.")

    now = timezone.now()
    active_sets = VitalRuleSet.objects.select_for_update().filter(status=VitalRuleSet.Status.ACTIVE)
    for active in active_sets:
        active.status = VitalRuleSet.Status.RETIRED
        active.active_marker = None
        active.effective_to = now
        active.save(update_fields=["status", "active_marker", "effective_to", "updated_at"])
        record_audit_event(
            actor=actor,
            request=request,
            action="vital_signs.vitalruleset.retired",
            object_type="vital_signs.VitalRuleSet",
            object_id=active.id,
            after={"status": active.status, "effective_to": now.isoformat()},
        )

    locked.status = VitalRuleSet.Status.ACTIVE
    locked.active_marker = 1
    locked.effective_from = now
    locked.effective_to = None
    locked.approved_by = actor
    locked.approved_at = now
    locked.save(
        update_fields=[
            "status",
            "active_marker",
            "effective_from",
            "effective_to",
            "approved_by",
            "approved_at",
            "updated_at",
        ]
    )
    record_audit_event(
        actor=actor,
        request=request,
        action="vital_signs.vitalruleset.activated",
        object_type="vital_signs.VitalRuleSet",
        object_id=locked.id,
        after={"status": locked.status, "effective_from": now.isoformat()},
    )
    return locked


@transaction.atomic
def retire_rule_set(*, rule_set: VitalRuleSet, actor, request=None) -> VitalRuleSet:
    locked = VitalRuleSet.objects.select_for_update().get(pk=rule_set.pk)
    if locked.status != VitalRuleSet.Status.ACTIVE:
        raise ValidationError("Only the active rule set can be retired.")
    now = timezone.now()
    locked.status = VitalRuleSet.Status.RETIRED
    locked.active_marker = None
    locked.effective_to = now
    locked.save(update_fields=["status", "active_marker", "effective_to", "updated_at"])
    record_audit_event(
        actor=actor,
        request=request,
        action="vital_signs.vitalruleset.retired",
        object_type="vital_signs.VitalRuleSet",
        object_id=locked.id,
        after={"status": locked.status, "effective_to": now.isoformat()},
    )
    return locked
