from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.billing.api.views import (
    BillingDashboardView,
    BillingPatientListView,
    ChargeItemViewSet,
    InvoiceViewSet,
    PaymentViewSet,
)

router = DefaultRouter()
router.register("charge-items", ChargeItemViewSet, basename="charge-item")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("payments", PaymentViewSet, basename="payment")

app_name = "billing"
urlpatterns = [
    path("billing/dashboard/", BillingDashboardView.as_view(), name="dashboard"),
    path("billing/patients/", BillingPatientListView.as_view(), name="patient-list"),
    *router.urls,
]
