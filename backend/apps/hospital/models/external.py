from django.db import models

from apps.common.models import UUIDTimeStampedModel

from .choices import AvailabilityStatus


class ExternalHospital(UUIDTimeStampedModel):
    name = models.CharField(max_length=180, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=2, default="CM")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32)
    transfer_email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ExternalHospitalSpecialty(UUIDTimeStampedModel):
    external_hospital = models.ForeignKey(
        ExternalHospital,
        on_delete=models.PROTECT,
        related_name="specialty_capabilities",
    )
    specialty = models.ForeignKey(
        "hospital.Specialty",
        on_delete=models.PROTECT,
        related_name="external_hospital_capabilities",
    )
    availability_status = models.CharField(
        max_length=16,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE,
    )
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["external_hospital__name", "specialty__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["external_hospital", "specialty"],
                name="unique_external_hospital_specialty",
            )
        ]

    def __str__(self) -> str:
        return f"{self.external_hospital} — {self.specialty}"


class ExternalSpecialist(UUIDTimeStampedModel):
    external_hospital = models.ForeignKey(
        ExternalHospital,
        on_delete=models.PROTECT,
        related_name="specialists",
    )
    specialty = models.ForeignKey(
        "hospital.Specialty",
        on_delete=models.PROTECT,
        related_name="external_specialists",
    )
    full_name = models.CharField(max_length=140)
    title = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["external_hospital__name", "full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["external_hospital", "full_name", "specialty"],
                name="unique_external_specialist_identity",
            )
        ]

    def __str__(self) -> str:
        return self.full_name


class ExternalHospitalService(UUIDTimeStampedModel):
    external_hospital = models.ForeignKey(
        ExternalHospital,
        on_delete=models.PROTECT,
        related_name="service_capabilities",
    )
    service = models.ForeignKey(
        "hospital.ServiceDefinition",
        on_delete=models.PROTECT,
        related_name="external_hospital_capabilities",
    )
    availability_status = models.CharField(
        max_length=16,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE,
    )
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["external_hospital__name", "service__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["external_hospital", "service"],
                name="unique_external_hospital_service",
            )
        ]

    def __str__(self) -> str:
        return f"{self.external_hospital} — {self.service}"
