from django.db import models

from apps.common.models import UUIDTimeStampedModel


class Medication(UUIDTimeStampedModel):
    generic_name = models.CharField(max_length=140)
    brand_name = models.CharField(max_length=140, blank=True)
    form = models.CharField(max_length=80)
    strength = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["generic_name", "brand_name", "strength"]
        constraints = [
            models.UniqueConstraint(
                fields=["generic_name", "brand_name", "form", "strength"],
                name="unique_medication_catalog_entry",
            )
        ]

    def __str__(self) -> str:
        brand = f" ({self.brand_name})" if self.brand_name else ""
        return f"{self.generic_name}{brand} {self.strength} {self.form}".strip()
