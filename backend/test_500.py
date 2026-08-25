import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
django.setup()

from apps.calls.models import CallSession
from apps.calls.services import signal_call

session = CallSession.objects.last()
if session:
    caller = session.initiated_by
    recipient = session.participants.exclude(user=caller).first().user
    
    print(f"Testing signal_call for session {session.id}...")
    try:
        # Callee requests offer from caller
        signal_call(
            session=session,
            sender=recipient,
            to_user=caller.id,
            data={"type": "request_offer"}
        )
        print("signal_call executed successfully!")
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print("No CallSession found.")
