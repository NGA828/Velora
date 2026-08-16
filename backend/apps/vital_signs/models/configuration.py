from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class VitalMetric(UUIDTimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=120, unique=True)
    unit = models.CharField(max_length=32)
    decimal_places = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
    )
    description = models.CharField(max_length=240, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.unit})"


class VitalRuleSet(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        RETIRED = "RETIRED", "Retired"

    name = models.CharField(max_length=140)
    version = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        editable=False,
    )
    active_marker = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        unique=True,
        editable=False,
    )
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_to = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vital_rule_sets_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "version"],
                name="unique_vital_rule_set_name_version",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"


class VitalRule(UUIDTimeStampedModel):
    class Operator(models.TextChoices):
        LESS_THAN = "LT", "Less than"
        LESS_THAN_OR_EQUAL = "LTE", "Less than or equal"
        GREATER_THAN = "GT", "Greater than"
        GREATER_THAN_OR_EQUAL = "GTE", "Greater than or equal"
        BETWEEN = "BETWEEN", "Between"
        OUTSIDE = "OUTSIDE", "Outside range"

    rule_set = models.ForeignKey(
        VitalRuleSet,
        on_delete=models.PROTECT,
        related_name="rules",
    )
    metric = models.ForeignKey(
        VitalMetric,
        on_delete=models.PROTECT,
        related_name="rules",
    )
    name = models.CharField(max_length=140)
    operator = models.CharField(max_length=12, choices=Operator.choices)
    lower_value = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    upper_value = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=100)
    explanation = models.CharField(max_length=300)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["priority", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["rule_set", "metric", "name"],
                name="unique_rule_name_per_metric_and_set",
            ),
            models.CheckConstraint(
                condition=models.Q(lower_value__isnull=False) | models.Q(upper_value__isnull=False),
                name="vital_rule_has_threshold",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.rule_set_id and self.rule_set.status != VitalRuleSet.Status.DRAFT:
            raise ValidationError("Rules can only be changed while the rule set is in draft.")
        if self.operator in {self.Operator.BETWEEN, self.Operator.OUTSIDE}:
            if self.lower_value is None or self.upper_value is None:
                raise ValidationError("Range operators require lower and upper values.")
            if self.lower_value >= self.upper_value:
                raise ValidationError("The lower value must be less than the upper value.")
        elif self.operator in {self.Operator.LESS_THAN, self.Operator.LESS_THAN_OR_EQUAL}:
            if self.upper_value is None:
                raise ValidationError("This operator requires an upper value.")
        elif self.lower_value is None:
            raise ValidationError("This operator requires a lower value.")

    def __str__(self) -> str:
        return f"{self.rule_set}: {self.name}"
