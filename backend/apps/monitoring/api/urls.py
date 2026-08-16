from rest_framework.routers import DefaultRouter

from apps.monitoring.api.views import MonitoringThreadViewSet

router = DefaultRouter()
router.register("monitoring-threads", MonitoringThreadViewSet, basename="monitoring-thread")

app_name = "monitoring"
urlpatterns = router.urls
