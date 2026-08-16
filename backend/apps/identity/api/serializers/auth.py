from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.identity.models import User
from apps.identity.policies import capabilities_for_role


class SessionUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "role",
            "role_label",
            "capabilities",
            "must_change_password",
        )

    def get_capabilities(self, user) -> tuple[str, ...]:
        return capabilities_for_role(user.role)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate_email(self, value: str) -> str:
        return User.objects.normalize_email(value).lower()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(trim_whitespace=False, write_only=True)
    new_password = serializers.CharField(trim_whitespace=False, write_only=True)
    confirm_password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError(
                {"old_password": "The current password is incorrect."}
            )
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "The new passwords do not match."}
            )
        validate_password(attrs["new_password"], user=user)
        return attrs
