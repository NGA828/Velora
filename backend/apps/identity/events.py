from django.dispatch import Signal

# Sent inside the invitation acceptance transaction. Receivers may attach
# domain-specific access records; receiver failures roll back acceptance.
invitation_accepted = Signal()
