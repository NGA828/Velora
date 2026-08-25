from django.contrib.auth.password_validation import validate_password
from django.urls import reverse
from rest_framework import serializers

from apps.identity.models import User
from apps.identity.policies import capabilities_for_role


class SessionUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    capabilities = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "avatar_url",
            "role",
            "role_label",
            "capabilities",
            "must_change_password",
        )

    def get_capabilities(self, user) -> tuple[str, ...]:
        return capabilities_for_role(user.role)

    def get_avatar_url(self, user) -> str | None:
        if not user.avatar:
            return None
        return reverse("identity:my-avatar")


class ProfileUpdateSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "avatar")
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
            "phone": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        if "first_name" in attrs and not attrs["first_name"].strip():
            raise serializers.ValidationError({"first_name": "First name cannot be blank."})
        if "last_name" in attrs and not attrs["last_name"].strip():
            raise serializers.ValidationError({"last_name": "Last name cannot be blank."})
        return attrs

    def validate_avatar(self, value):
        if value is None:
            return value
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Profile picture must be 5 MB or smaller.")
        if value.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise serializers.ValidationError("Use a JPEG, PNG or WebP image.")
        return value


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
