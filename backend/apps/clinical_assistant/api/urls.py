from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.clinical_assistant.api.views import ChatAPIView, SessionViewSet

router = DefaultRouter()
router.register(r"clinical-assistant/sessions", SessionViewSet, basename="clinical-assistant-sessions")

urlpatterns = [
    path("clinical-assistant/chat/", ChatAPIView.as_view(), name="clinical-assistant-chat"),
    path("", include(router.urls)),
]
