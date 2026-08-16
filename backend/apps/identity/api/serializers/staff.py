from rest_framework import serializers

from apps.identity.models import StaffProfile


class StaffProfileUpdateSerializer(serializers.ModelSerializer):
    account_active = serializers.BooleanField(source="user.is_active", required=False)

    class Meta:
        model = StaffProfile
        fields = (
            "department",
            "job_title",
            "license_number",
            "hire_date",
            "employment_status",
            "account_active",
        )

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        instance = super().update(instance, validated_data)
        if "is_active" in user_data:
            instance.user.is_active = user_data["is_active"]
            instance.user.save(update_fields=["is_active", "updated_at"])
        return instance


class StaffProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    role_label = serializers.CharField(source="user.get_role_display", read_only=True)
    account_active = serializers.BooleanField(source="user.is_active", read_only=True)
    department_name = serializers.CharField(
        source="department.name", read_only=True, allow_null=True, default=None
    )

    class Meta:
        model = StaffProfile
        fields = (
            "id",
            "user_id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "role_label",
            "account_active",
            "employee_number",
            "department",
            "department_name",
            "job_title",
            "license_number",
            "hire_date",
            "employment_status",
        )
