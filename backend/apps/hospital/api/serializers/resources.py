from rest_framework import serializers

from apps.hospital.models import Bed, Resource, Room


class RoomSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    bed_count = serializers.IntegerField(read_only=True, default=0)
    available_bed_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Room
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class BedSerializer(serializers.ModelSerializer):
    room_code = serializers.CharField(source="room.code", read_only=True)
    department_name = serializers.CharField(source="room.department.name", read_only=True)

    class Meta:
        model = Bed
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ResourceSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Resource
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        total = attrs.get("quantity_total", getattr(self.instance, "quantity_total", None))
        available = attrs.get(
            "quantity_available", getattr(self.instance, "quantity_available", None)
        )
        if total is not None and available is not None and available > total:
            raise serializers.ValidationError(
                {"quantity_available": "Available quantity cannot exceed total quantity."}
            )
        return attrs
