from django.db import models


class AvailabilityStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    LIMITED = "LIMITED", "Limited"
    UNAVAILABLE = "UNAVAILABLE", "Unavailable"


class OperationalStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    MAINTENANCE = "MAINTENANCE", "Maintenance"
    CLOSED = "CLOSED", "Closed"
