import hashlib
import json
from urllib.parse import urlencode

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from twilio.twiml.voice_response import Dial, VoiceResponse

from apps.calls.models import CallParticipant, CallSession, CallWebhookEvent
from apps.messaging.realtime import publish_user_event
from integrations.twilio.config import get_twilio_settings
from integrations.twilio.signatures import valid_twilio_signature

STATUS_MAP = {
    "queued": CallSession.Status.QUEUED,
    "initiated": CallSession.Status.QUEUED,
    "ringing": CallSession.Status.RINGING,
    "in-progress": CallSession.Status.IN_PROGRESS,
    "answered": CallSession.Status.IN_PROGRESS,
    "completed": CallSession.Status.COMPLETED,
    "busy": CallSession.Status.DECLINED,
    "no-answer": CallSession.Status.NO_ANSWER,
    "failed": CallSession.Status.FAILED,
    "canceled": CallSession.Status.CANCELLED,
}


def _invalid_signature():
    return JsonResponse({"detail": "Invalid Twilio signature."}, status=403)


@method_decorator(csrf_exempt, name="dispatch")
class TwilioVoiceWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not valid_twilio_signature(request):
            return _invalid_signature()
        session_id = request.POST.get("call_session_id")
        try:
            session = CallSession.objects.prefetch_related("participants").get(pk=session_id)
        except (CallSession.DoesNotExist, ValueError):
            return JsonResponse({"detail": "Call session not found."}, status=404)
        recipient = session.participants.exclude(user=session.initiated_by).first()
        if not recipient:
            return JsonResponse({"detail": "Call recipient not found."}, status=400)
        session.provider_sid = request.POST.get("CallSid", "")[:80]
        session.status = CallSession.Status.RINGING
        session.ringing_at = timezone.now()
        session.save(update_fields=["provider_sid", "status", "ringing_at", "updated_at"])
        config = get_twilio_settings()
        callback = (
            f"{config.webhook_base_url}/api/v1/integrations/twilio/status/?"
            f"{urlencode({'call_session_id': str(session.id)})}"
        )
        response = VoiceResponse()
        dial = Dial(answer_on_bridge=True)
        dial.client(
            recipient.provider_identity,
            status_callback=callback,
            status_callback_event="initiated ringing answered completed",
        )
        response.append(dial)
        return HttpResponse(str(response), content_type="text/xml")


@method_decorator(csrf_exempt, name="dispatch")
class TwilioStatusWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not valid_twilio_signature(request):
            return _invalid_signature()
        session_id = request.GET.get("call_session_id")
        provider_status = request.POST.get("CallStatus", "").lower()
        provider_sid = request.POST.get("CallSid", "")
        payload_hash = hashlib.sha256(
            json.dumps(request.POST.dict(), sort_keys=True).encode("utf-8")
        ).hexdigest()
        event_id = hashlib.sha256(
            f"{session_id}:{provider_sid}:{provider_status}:{payload_hash}".encode()
        ).hexdigest()
        event, created = CallWebhookEvent.objects.get_or_create(
            provider_event_id=event_id,
            defaults={
                "event_type": provider_status,
                "payload_hash": payload_hash,
                "received_at": timezone.now(),
            },
        )
        if not created and event.processed_at:
            return JsonResponse({"received": True, "duplicate": True})
        try:
            session = CallSession.objects.get(pk=session_id)
            event.call_session = session
            session.provider_sid = provider_sid[:80]
            session.status = STATUS_MAP.get(provider_status, CallSession.Status.FAILED)
            now = timezone.now()
            if session.status == CallSession.Status.RINGING and not session.ringing_at:
                session.ringing_at = now
            if session.status == CallSession.Status.IN_PROGRESS and not session.answered_at:
                session.answered_at = now
                session.participants.update(
                    status=CallParticipant.Status.CONNECTED,
                    joined_at=now,
                )
            if session.status in {
                CallSession.Status.COMPLETED,
                CallSession.Status.DECLINED,
                CallSession.Status.NO_ANSWER,
                CallSession.Status.FAILED,
                CallSession.Status.CANCELLED,
            }:
                session.ended_at = now
                session.participants.update(
                    status=CallParticipant.Status.LEFT,
                    left_at=now,
                )
            session.save()
            event.processed_at = now
            event.save(update_fields=["call_session", "processed_at", "updated_at"])
            for user_id in session.participants.values_list("user_id", flat=True):
                publish_user_event(
                    user_id=user_id,
                    event_type="call.updated",
                    payload={
                        "call_session_id": str(session.id),
                        "status": session.status,
                    },
                )
        except Exception as exc:
            event.processing_error = str(exc)[:500]
            event.save(update_fields=["processing_error", "updated_at"])
            return JsonResponse({"received": False}, status=500)
        return JsonResponse({"received": True})
