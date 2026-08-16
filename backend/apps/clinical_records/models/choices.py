from django.db import models


class GuardianVisibility(models.TextChoices):
    INTERNAL = "INTERNAL", "Clinical team only"
    GUARDIAN = "GUARDIAN", "Visible to Patient Guard"
