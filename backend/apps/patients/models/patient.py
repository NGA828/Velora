from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.models import UUIDTimeStampedModel


class Patient(UUIDTimeStampedModel):
    class SexAtBirth(models.TextChoices):
        FEMALE = "FEMALE", "Female"
        MALE = "MALE", "Male"
        INTERSEX = "INTERSEX", "Intersex"
        NOT_RECORDED = "NOT_RECORDED", "Not recorded"

    class Status(models.TextChoices):
        REGISTERED = "REGISTERED", "Registered"
        ADMITTED = "ADMITTED", "Admitted"
        DISCHARGED = "DISCHARGED", "Discharged"
        TRANSFERRED = "TRANSFERRED", "Transferred"
        DECEASED = "DECEASED", "Deceased"
        ARCHIVED = "ARCHIVED", "Archived"

    medical_record_number = models.CharField(max_length=32, unique=True, db_index=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    date_of_birth = models.DateField()
    sex_at_birth = models.CharField(max_length=16, choices=SexAtBirth.choices)
    gender_identity = models.CharField(max_length=80, blank=True)
    blood_type = models.CharField(max_length=8, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField()
    emergency_contact_name = models.CharField(max_length=140)
    emergency_contact_phone = models.CharField(max_length=32)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.REGISTERED,
        db_index=True,
    )
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="patients_registered",
    )

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["last_name", "first_name"]),
        ]

    def clean(self) -> None:
        super().clean()
        if self.date_of_birth and self.date_of_birth > timezone.localdate():
            raise ValidationError({"date_of_birth": "Date of birth cannot be in the future."})

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return f"{self.medical_record_number} — {self.get_full_name()}"
