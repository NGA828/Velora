from rest_framework import serializers

from apps.hospital.models import Department
from apps.identity.models import Invitation, UserRole


class InvitationSerializer(serializers.ModelSerializer):
    intended_role_label = serializers.CharField(source="get_intended_role_display", read_only=True)
    invited_by_name = serializers.CharField(source="invited_by.get_full_name", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = (
            "id",
            "email",
            "intended_role",
            "intended_role_label",
            "invited_by_name",
            "expires_at",
            "accepted_at",
            "revoked_at",
            "status",
            "created_at",
        )

    def get_status(self, invitation) -> str:
        if invitation.accepted_at:
            return "ACCEPTED"
        if invitation.revoked_at:
            return "REVOKED"
        if invitation.is_expired:
            return "EXPIRED"
        return "PENDING"


class StaffInvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    intended_role = serializers.ChoiceField(
        choices=[
            UserRole.ADMIN,
            UserRole.HEAD_OF_SERVICE,
            UserRole.DOCTOR,
            UserRole.NURSE,
            UserRole.ACCOUNTING,
        ]
    )
    employee_number = serializers.CharField(max_length=32)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True),
        source="department",
        required=False,
        allow_null=True,
    )
    job_title = serializers.CharField(max_length=120, required=False, allow_blank=True)
    license_number = serializers.CharField(max_length=80, required=False, allow_blank=True)
    hire_date = serializers.DateField(required=False, allow_null=True)

    def validate_email(self, value: str) -> str:
        return value.lower()

    def invitation_context(self) -> dict:
        data = self.validated_data
        department = data.get("department")
        hire_date = data.get("hire_date")
        return {
            "employee_number": data["employee_number"],
            "department_id": str(department.id) if department else None,
            "job_title": data.get("job_title", ""),
            "license_number": data.get("license_number", ""),
            "hire_date": hire_date.isoformat() if hire_date else None,
        }


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField(min_length=20, trim_whitespace=True, write_only=True)
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    password = serializers.CharField(trim_whitespace=False, write_only=True)
    confirm_password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "The passwords do not match."})
        return attrs
