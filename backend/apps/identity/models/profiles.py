from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class EmploymentStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    ON_LEAVE = "ON_LEAVE", "On leave"
    INACTIVE = "INACTIVE", "Inactive"


class StaffProfile(UUIDTimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="staff_profile",
    )
    employee_number = models.CharField(max_length=32, unique=True)
    department = models.ForeignKey(
        "hospital.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="staff_members",
    )
    job_title = models.CharField(max_length=120, blank=True)
    license_number = models.CharField(max_length=80, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    employment_status = models.CharField(
        max_length=16,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.ACTIVE,
        db_index=True,
    )

    class Meta:
        ordering = ["employee_number"]

    def __str__(self) -> str:
        return f"{self.employee_number} — {self.user.get_full_name()}"


class PatientGuardProfile(UUIDTimeStampedModel):
    class ContactMethod(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        PHONE = "PHONE", "Phone"
        SMS = "SMS", "SMS"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="patient_guard_profile",
    )
    address = models.TextField(blank=True)
    preferred_language = models.CharField(max_length=16, default="en")
    preferred_contact_method = models.CharField(
        max_length=16,
        choices=ContactMethod.choices,
        default=ContactMethod.EMAIL,
    )

    def __str__(self) -> str:
        return self.user.get_full_name()
