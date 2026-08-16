from rest_framework.filters import OrderingFilter, SearchFilter

from apps.common.viewsets import AuditedNoDestroyModelViewSet
from apps.hospital.permissions import HospitalConfigurationPermission


class HospitalConfigurationViewSet(AuditedNoDestroyModelViewSet):
    permission_classes = [HospitalConfigurationPermission]
    filter_backends = [SearchFilter, OrderingFilter]
    ordering = ["-created_at"]
