from rest_framework.routers import DefaultRouter

from apps.vital_signs.api.views import (
    VitalMetricViewSet,
    VitalObservationViewSet,
    VitalRuleSetViewSet,
    VitalRuleViewSet,
)

router = DefaultRouter()
router.register("vital-metrics", VitalMetricViewSet, basename="vital-metric")
router.register("vital-rule-sets", VitalRuleSetViewSet, basename="vital-rule-set")
router.register("vital-rules", VitalRuleViewSet, basename="vital-rule")
router.register("vital-observations", VitalObservationViewSet, basename="vital-observation")

app_name = "vital_signs"
urlpatterns = router.urls
