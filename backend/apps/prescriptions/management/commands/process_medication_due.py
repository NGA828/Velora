import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.audit.models import SystemHeartbeat
from apps.prescriptions.services import process_due_dose_notifications


class Command(BaseCommand):
    help = "Create idempotent notifications for medication doses whose scheduled time has arrived."

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch", action="store_true", help="Continue processing until stopped."
        )
        parser.add_argument("--interval", type=int, default=30, help="Seconds between watch runs.")

    def handle(self, *args, **options):
        interval = max(5, options["interval"])
        while True:
            count = process_due_dose_notifications()
            SystemHeartbeat.objects.update_or_create(
                service="medication-reminder-worker",
                defaults={
                    "status": "HEALTHY",
                    "last_seen_at": timezone.now(),
                    "details": {"alerts_created": count},
                },
            )
            if count:
                self.stdout.write(self.style.SUCCESS(f"Sent alerts for {count} due doses."))
            if not options["watch"]:
                break
            time.sleep(interval)
