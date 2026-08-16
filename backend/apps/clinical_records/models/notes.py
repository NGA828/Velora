from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel

from .choices import GuardianVisibility


class ClinicalNote(UUIDTimeStampedModel):
    class NoteType(models.TextChoices):
        PROGRESS = "PROGRESS", "Progress note"
        CONSULTATION = "CONSULTATION", "Consultation note"
        NURSING = "NURSING", "Nursing note"
        DISCHARGE = "DISCHARGE", "Discharge note"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SIGNED = "SIGNED", "Signed"

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="clinical_notes"
    )
    care_episode = models.ForeignKey(
        "patients.CareEpisode",
        on_delete=models.PROTECT,
        related_name="clinical_notes",
        null=True,
        blank=True,
    )
    note_type = models.CharField(max_length=16, choices=NoteType.choices)
    title = models.CharField(max_length=180)
    body = models.TextField()
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    signed_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clinical_notes_authored",
    )
    amends = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="amendments",
        null=True,
        blank=True,
    )
    guardian_visibility = models.CharField(
        max_length=12,
        choices=GuardianVisibility.choices,
        default=GuardianVisibility.INTERNAL,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
