import getpass
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.identity.models import StaffProfile, User


class Command(BaseCommand):
    help = "Create the first Velora Admin account without exposing a password in command history."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--first-name", required=True)
        parser.add_argument("--last-name", required=True)
        parser.add_argument("--employee-number", required=True)
        parser.add_argument("--no-input", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        email = options["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError("A user with this email already exists.")

        password = os.getenv("VELORA_BOOTSTRAP_PASSWORD")
        if not password and not options["no_input"]:
            password = getpass.getpass("Initial password: ")
            confirmation = getpass.getpass("Confirm password: ")
            if password != confirmation:
                raise CommandError("Passwords do not match.")
        if not password:
            raise CommandError(
                "Set VELORA_BOOTSTRAP_PASSWORD when using --no-input. "
                "Do not pass passwords as command arguments."
            )

        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name=options["first_name"],
            last_name=options["last_name"],
            must_change_password=True,
        )
        StaffProfile.objects.create(
            user=user,
            employee_number=options["employee_number"],
            job_title="System Administrator",
        )
        self.stdout.write(self.style.SUCCESS(f"Created Admin account for {email}."))
