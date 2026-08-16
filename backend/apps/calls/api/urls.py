from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.calls.api.views import (
    CallSessionViewSet,
    TwilioStatusWebhookView,
    TwilioVoiceWebhookView,
)

router = DefaultRouter()
router.register("calls", CallSessionViewSet, basename="call")

app_name = "calls"
urlpatterns = [
    path(
        "integrations/twilio/voice/",
        TwilioVoiceWebhookView.as_view(),
        name="twilio-voice",
    ),
    path(
        "integrations/twilio/status/",
        TwilioStatusWebhookView.as_view(),
        name="twilio-status",
    ),
    *router.urls,
]
