from rest_framework.routers import DefaultRouter

from apps.messaging.api.views import ConversationViewSet

router = DefaultRouter()
router.register("conversations", ConversationViewSet, basename="conversation")

app_name = "messaging"
urlpatterns = router.urls
