from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class VitalObservation(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        UNASSESSED = "UNASSESSED", "Unassessed"
        STABLE = "STABLE", "Stable"
        CRITICAL = "CRITICAL", "Critical"

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="vital_observations",
    )
    care_episode = models.ForeignKey(
        "patients.CareEpisode",
        on_delete=models.PROTECT,
        related_name="vital_observations",
        null=True,
        blank=True,
    )
    observed_at = models.DateTimeField(db_index=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vital_observations_recorded",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.UNASSESSED,
        db_index=True,
    )
    stability_percent = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    criticality_percent = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    assessed_metric_count = models.PositiveSmallIntegerField(default=0)
    critical_metric_count = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    rule_set = models.ForeignKey(
        "vital_signs.VitalRuleSet",
        on_delete=models.PROTECT,
        related_name="observations_analyzed",
        null=True,
        blank=True,
    )
    rule_set_name_snapshot = models.CharField(max_length=140, blank=True)
    rule_set_version_snapshot = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-observed_at", "-created_at"]
        indexes = [models.Index(fields=["patient", "-observed_at"])]

    def __str__(self) -> str:
        return f"{self.patient} — {self.observed_at:%Y-%m-%d %H:%M}"


class VitalValue(UUIDTimeStampedModel):
    observation = models.ForeignKey(
        VitalObservation,
        on_delete=models.PROTECT,
        related_name="values",
    )
    metric = models.ForeignKey(
        "vital_signs.VitalMetric",
        on_delete=models.PROTECT,
        related_name="observed_values",
    )
    value = models.DecimalField(max_digits=12, decimal_places=4)

    class Meta:
        ordering = ["metric__display_order", "metric__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["observation", "metric"],
                name="unique_metric_per_vital_observation",
            )
        ]

    def __str__(self) -> str:
        return f"{self.metric}: {self.value}"


class VitalRuleEvaluation(UUIDTimeStampedModel):
    observation = models.ForeignKey(
        VitalObservation,
        on_delete=models.PROTECT,
        related_name="evaluations",
    )
    value = models.ForeignKey(
        VitalValue,
        on_delete=models.PROTECT,
        related_name="evaluations",
    )
    rule = models.ForeignKey(
        "vital_signs.VitalRule",
        on_delete=models.PROTECT,
        related_name="evaluations",
    )
    matched = models.BooleanField(db_index=True)
    measured_value = models.DecimalField(max_digits=12, decimal_places=4)
    rule_name_snapshot = models.CharField(max_length=140)
    metric_name_snapshot = models.CharField(max_length=120)
    metric_unit_snapshot = models.CharField(max_length=32)
    operator_snapshot = models.CharField(max_length=12)
    lower_value_snapshot = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    upper_value_snapshot = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    explanation = models.CharField(max_length=400)

    class Meta:
        ordering = ["rule__priority", "rule_name_snapshot"]
        constraints = [
            models.UniqueConstraint(
                fields=["observation", "value", "rule"],
                name="unique_rule_evaluation_per_observed_value",
            )
        ]

    def __str__(self) -> str:
        return f"{self.rule_name_snapshot}: {'matched' if self.matched else 'not matched'}"


class IcuRecommendation(UUIDTimeStampedModel):
    observation = models.OneToOneField(
        VitalObservation,
        on_delete=models.PROTECT,
        related_name="icu_recommendation",
    )
    eligible = models.BooleanField(default=False)
    score = models.PositiveSmallIntegerField(default=0)
    specialist_status = models.CharField(max_length=120)
    icu_bed_status = models.CharField(max_length=120)
    explanation = models.TextField()
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self) -> str:
        return f"ICU Recommendation for {self.observation}"

