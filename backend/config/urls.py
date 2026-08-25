from django.contrib import admin
from django.urls import include, path

from apps.common.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    path("api/v1/", include("apps.identity.api.urls")),
    path("api/v1/", include("apps.hospital.api.urls")),
    path("api/v1/", include("apps.patients.api.urls")),
    path("api/v1/", include("apps.clinical_records.api.urls")),
    path("api/v1/", include("apps.prescriptions.api.urls")),
    path("api/v1/", include("apps.vital_signs.api.urls")),
    path("api/v1/", include("apps.monitoring.api.urls")),
    path("api/v1/", include("apps.transfers.api.urls")),
    path("api/v1/", include("apps.death_certificates.api.urls")),
    path("api/v1/", include("apps.messaging.api.urls")),
    path("api/v1/", include("apps.calls.api.urls")),
    path("api/v1/", include("apps.billing.api.urls")),
    path("api/v1/", include("apps.reports.api.urls")),
    path("api/v1/", include("apps.notifications.api.urls")),
    path("api/v1/", include("apps.clinical_assistant.api.urls")),
]
