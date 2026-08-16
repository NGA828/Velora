import os

from django.conf import settings
from django.core.mail import send_mail


def send_invitation_email(*, invitation, raw_token: str) -> int:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    acceptance_url = f"{frontend_url}/accept-invitation#token={raw_token}"
    subject = f"You have been invited to Velora as {invitation.get_intended_role_display()}"
    body = (
        "You have been invited to access the Velora hospital system.\n\n"
        f"Accept your invitation: {acceptance_url}\n\n"
        f"This invitation expires at {invitation.expires_at.isoformat()}. "
        "If you did not expect it, do not open the link."
    )
    return send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [invitation.email])
