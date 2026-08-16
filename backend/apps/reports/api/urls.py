from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.reports.api.views import (
    FinancialReportExportView,
    FinancialReportView,
    OperationalReportView,
    RedactedAuditEventViewSet,
    SystemDashboardView,
    SystemUserViewSet,
)

router = DefaultRouter()
router.register("system/users", SystemUserViewSet, basename="system-user")
router.register("system/audit", RedactedAuditEventViewSet, basename="system-audit")

app_name = "reports"
urlpatterns = [
    path("reports/financial/", FinancialReportView.as_view(), name="financial"),
    path(
        "reports/financial/export/",
        FinancialReportExportView.as_view(),
        name="financial-export",
    ),
    path("reports/operational/", OperationalReportView.as_view(), name="operational"),
    path("system/dashboard/", SystemDashboardView.as_view(), name="system-dashboard"),
    *router.urls,
]
