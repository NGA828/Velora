from django.db import models

from apps.common.models import UUIDTimeStampedModel


class Department(UUIDTimeStampedModel):
    code = models.CharField(max_length=24, unique=True)
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=180, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    head = models.ForeignKey(
        "identity.StaffProfile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="departments_led",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"
