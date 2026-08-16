from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import UUIDTimeStampedModel

from .choices import OperationalStatus


class Room(UUIDTimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    department = models.ForeignKey(
        "hospital.Department",
        on_delete=models.PROTECT,
        related_name="rooms",
    )
    floor = models.CharField(max_length=40, blank=True)
    room_type = models.CharField(max_length=80)
    status = models.CharField(
        max_length=16,
        choices=OperationalStatus.choices,
        default=OperationalStatus.ACTIVE,
        db_index=True,
    )

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class Bed(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        OCCUPIED = "OCCUPIED", "Occupied"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        UNAVAILABLE = "UNAVAILABLE", "Unavailable"

    code = models.CharField(max_length=32)
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="beds")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.AVAILABLE,
        db_index=True,
    )
    notes = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ["room__code", "code"]
        constraints = [
            models.UniqueConstraint(fields=["room", "code"], name="unique_bed_code_per_room")
        ]

    def __str__(self) -> str:
        return f"{self.room.code}/{self.code}"


class Resource(UUIDTimeStampedModel):
    class Category(models.TextChoices):
        EQUIPMENT = "EQUIPMENT", "Equipment"
        SUPPLY = "SUPPLY", "Supply"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        LIMITED = "LIMITED", "Limited"
        UNAVAILABLE = "UNAVAILABLE", "Unavailable"
        MAINTENANCE = "MAINTENANCE", "Maintenance"

    asset_code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=140)
    category = models.CharField(max_length=16, choices=Category.choices)
    department = models.ForeignKey(
        "hospital.Department",
        on_delete=models.PROTECT,
        related_name="resources",
    )
    quantity_total = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    quantity_available = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.AVAILABLE,
        db_index=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name", "asset_code"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_available__lte=models.F("quantity_total")),
                name="resource_available_not_more_than_total",
            )
        ]

    def __str__(self) -> str:
        return f"{self.asset_code} — {self.name}"
