from django.db import models

from apps.common.models import UUIDTimeStampedModel


class HospitalProfile(UUIDTimeStampedModel):
    singleton_key = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    legal_name = models.CharField(max_length=180)
    display_name = models.CharField(max_length=120)
    registration_number = models.CharField(max_length=80, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=2, default="CM")
    email = models.EmailField()
    phone = models.CharField(max_length=32)
    website = models.URLField(blank=True)
    timezone = models.CharField(max_length=64, default="Africa/Lagos")
    billing_currency = models.CharField(
        max_length=3,
        default="XAF",
        help_text="ISO 4217 currency code used for new financial records.",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(singleton_key=1),
                name="hospital_profile_singleton_key_is_one",
            )
        ]

    def __str__(self) -> str:
        return self.display_name
