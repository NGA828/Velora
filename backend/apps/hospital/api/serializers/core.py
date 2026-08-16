from rest_framework import serializers

from apps.hospital.models import Department, HospitalProfile


class HospitalProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = HospitalProfile
        exclude = ("singleton_key",)
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_billing_currency(self, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise serializers.ValidationError("Enter a three-letter ISO 4217 currency code.")
        return normalized


class DepartmentSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)
    head_name = serializers.CharField(
        source="head.user.get_full_name", read_only=True, default=None
    )
    staff_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Department
        fields = (
            "id",
            "code",
            "name",
            "description",
            "location",
            "phone",
            "is_active",
            "parent",
            "parent_name",
            "head",
            "head_name",
            "staff_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_parent(self, value):
        if self.instance and value and value.pk == self.instance.pk:
            raise serializers.ValidationError("A department cannot be its own parent.")
        return value
