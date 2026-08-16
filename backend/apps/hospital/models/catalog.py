from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import UUIDTimeStampedModel

from .choices import AvailabilityStatus


class Specialty(UUIDTimeStampedModel):
    code = models.CharField(max_length=24, unique=True)
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "specialties"

    def __str__(self) -> str:
        return self.name


class ClinicalCondition(UUIDTimeStampedModel):
    coding_system = models.CharField(max_length=32, default="LOCAL")
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["coding_system", "code"],
                name="unique_condition_code_per_system",
            )
        ]

    def __str__(self) -> str:
        return self.name


class SpecialtyCondition(UUIDTimeStampedModel):
    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.PROTECT,
        related_name="condition_mappings",
    )
    condition = models.ForeignKey(
        ClinicalCondition,
        on_delete=models.PROTECT,
        related_name="specialty_mappings",
    )
    match_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.10")), MaxValueValidator(Decimal("100.00"))],
    )
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["specialty__name", "condition__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["specialty", "condition"],
                name="unique_specialty_condition_mapping",
            )
        ]

    def __str__(self) -> str:
        return f"{self.specialty} → {self.condition}"


class ServiceDefinition(UUIDTimeStampedModel):
    code = models.CharField(max_length=24, unique=True)
    name = models.CharField(max_length=140, unique=True)
    category = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class HospitalServiceAvailability(UUIDTimeStampedModel):
    service = models.ForeignKey(
        ServiceDefinition,
        on_delete=models.PROTECT,
        related_name="hospital_availability",
    )
    department = models.ForeignKey(
        "hospital.Department",
        on_delete=models.PROTECT,
        related_name="service_availability",
    )
    availability_status = models.CharField(
        max_length=16,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE,
        db_index=True,
    )
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["service__name", "department__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "department"],
                name="unique_internal_service_department",
            )
        ]

    def __str__(self) -> str:
        return f"{self.service} — {self.department}"
