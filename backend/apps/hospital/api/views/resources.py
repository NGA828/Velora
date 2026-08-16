from django.db.models import Count, Q

from apps.hospital.api.serializers import BedSerializer, ResourceSerializer, RoomSerializer
from apps.hospital.models import Bed, Resource, Room

from .base import HospitalConfigurationViewSet


class RoomViewSet(HospitalConfigurationViewSet):
    serializer_class = RoomSerializer
    search_fields = ["code", "room_type", "floor", "department__name"]
    ordering_fields = ["code", "room_type", "floor", "status"]
    ordering = ["code"]

    def get_queryset(self):
        queryset = Room.objects.select_related("department").annotate(
            bed_count=Count("beds", distinct=True),
            available_bed_count=Count(
                "beds", filter=Q(beds__status=Bed.Status.AVAILABLE), distinct=True
            ),
        )
        department = self.request.query_params.get("department")
        if department:
            queryset = queryset.filter(department_id=department)
        return queryset


class BedViewSet(HospitalConfigurationViewSet):
    serializer_class = BedSerializer
    search_fields = ["code", "room__code", "room__department__name"]
    ordering_fields = ["code", "room__code", "status"]
    ordering = ["room__code", "code"]

    def get_queryset(self):
        queryset = Bed.objects.select_related("room", "room__department")
        room = self.request.query_params.get("room")
        if room:
            queryset = queryset.filter(room_id=room)
        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)
        return queryset


class ResourceViewSet(HospitalConfigurationViewSet):
    serializer_class = ResourceSerializer
    search_fields = ["asset_code", "name", "department__name"]
    ordering_fields = ["asset_code", "name", "status", "quantity_available"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = Resource.objects.select_related("department")
        department = self.request.query_params.get("department")
        if department:
            queryset = queryset.filter(department_id=department)
        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)
        return queryset
