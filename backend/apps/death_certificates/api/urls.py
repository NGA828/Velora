from rest_framework.routers import DefaultRouter

from apps.death_certificates.api.views import DeathCertificateViewSet

router = DefaultRouter()
router.register("death-certificates", DeathCertificateViewSet, basename="death-certificate")

app_name = "death_certificates"
urlpatterns = router.urls
