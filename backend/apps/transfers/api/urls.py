from rest_framework.routers import DefaultRouter

from apps.transfers.api.views import TransferRequestViewSet

router = DefaultRouter()
router.register("transfer-requests", TransferRequestViewSet, basename="transfer-request")

app_name = "transfers"
urlpatterns = router.urls
