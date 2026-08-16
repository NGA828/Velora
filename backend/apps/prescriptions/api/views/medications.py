from apps.common.viewsets import AuditedNoDestroyModelViewSet
from apps.prescriptions.api.serializers import MedicationSerializer
from apps.prescriptions.models import Medication
from apps.prescriptions.permissions import MedicationCatalogPermission


class MedicationViewSet(AuditedNoDestroyModelViewSet):
    serializer_class = MedicationSerializer
    permission_classes = [MedicationCatalogPermission]
    queryset = Medication.objects.all()
    search_fields = ["generic_name", "brand_name", "form", "strength"]

    def get_queryset(self):
        queryset = Medication.objects.all()
        active = self.request.query_params.get("is_active")
        if active in {"true", "false"}:
            queryset = queryset.filter(is_active=active == "true")
        return queryset
