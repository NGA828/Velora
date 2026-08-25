from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test email through the configured SMTP backend to verify email delivery."

    def add_arguments(self, parser):
        parser.add_argument("recipient", help="Email address that receives the test message.")

    def handle(self, *args, **options):
        recipient = options["recipient"]
        try:
            sent = send_mail(
                subject="Velora — SMTP test message",
                message=(
                    "This email confirms that Velora's email service is configured "
                    "correctly. Invitations, notifications and authorized medical "
                    "transfer packages will be delivered through this channel."
                ),
                from_email=None,
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception as exc:  # pragma: no cover - depends on external SMTP
            raise CommandError(f"Email delivery failed: {exc}") from exc
        if sent != 1:
            raise CommandError("Email delivery failed: no messages were accepted.")
        self.stdout.write(self.style.SUCCESS(f"Test email sent to {recipient}."))
