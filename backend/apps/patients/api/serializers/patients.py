from django.utils import timezone
from rest_framework import serializers

from apps.hospital.models import Department
from apps.identity.models import EmploymentStatus, StaffProfile, UserRole
from apps.patients.models import CareEpisode, Patient, PatientCareAssignment


class CareTeamMemberSerializer(serializers.ModelSerializer):
    staff_id = serializers.UUIDField(source="staff.id", read_only=True)
    user_id = serializers.UUIDField(source="staff.user.id", read_only=True)
    full_name = serializers.CharField(source="staff.user.get_full_name", read_only=True)
    role = serializers.CharField(source="assignment_type", read_only=True)
    job_title = serializers.CharField(source="staff.job_title", read_only=True)

    class Meta:
        model = PatientCareAssignment
        fields = (
            "id",
            "staff_id",
            "user_id",
            "full_name",
            "role",
            "job_title",
            "is_primary",
            "starts_at",
        )


class CareEpisodeSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    episode_type_label = serializers.CharField(source="get_episode_type_display", read_only=True)

    class Meta:
        model = CareEpisode
        fields = (
            "id",
            "episode_number",
            "episode_type",
            "episode_type_label",
            "department",
            "department_name",
            "admission_reason",
            "admitted_at",
            "discharged_at",
            "status",
        )


class PatientListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    age = serializers.SerializerMethodField()
    primary_doctor = serializers.SerializerMethodField()
    primary_nurse = serializers.SerializerMethodField()
    current_department = serializers.SerializerMethodField()
    active_guardian_count = serializers.IntegerField(read_only=True, default=0)
    latest_vital_status = serializers.CharField(read_only=True, allow_null=True, default=None)
    latest_vital_at = serializers.DateTimeField(read_only=True, allow_null=True, default=None)

    class Meta:
        model = Patient
        fields = (
            "id",
            "medical_record_number",
            "first_name",
            "last_name",
            "full_name",
            "date_of_birth",
            "age",
            "sex_at_birth",
            "status",
            "primary_doctor",
            "primary_nurse",
            "current_department",
            "active_guardian_count",
            "latest_vital_status",
            "latest_vital_at",
            "created_at",
        )

    def get_age(self, patient) -> int:
        today = timezone.localdate()
        return (
            today.year
            - patient.date_of_birth.year
            - ((today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day))
        )

    @staticmethod
    def _assignment(patient, assignment_type):
        assignments = getattr(patient, "active_assignments", None)
        if assignments is None:
            assignments = patient.care_assignments.filter(ends_at__isnull=True).select_related(
                "staff__user"
            )
        return next(
            (item for item in assignments if item.assignment_type == assignment_type),
            None,
        )

    def get_primary_doctor(self, patient):
        assignment = self._assignment(patient, PatientCareAssignment.AssignmentType.DOCTOR)
        return (
            {"staff_id": str(assignment.staff_id), "name": assignment.staff.user.get_full_name()}
            if assignment
            else None
        )

    def get_primary_nurse(self, patient):
        assignment = self._assignment(patient, PatientCareAssignment.AssignmentType.NURSE)
        return (
            {"staff_id": str(assignment.staff_id), "name": assignment.staff.user.get_full_name()}
            if assignment
            else None
        )

    def get_current_department(self, patient):
        episodes = getattr(patient, "active_episodes", None)
        episode = (
            episodes[0]
            if episodes
            else patient.care_episodes.filter(status="ACTIVE").select_related("department").first()
        )
        return (
            {"id": str(episode.department_id), "name": episode.department.name} if episode else None
        )


class PatientDetailSerializer(PatientListSerializer):
    care_team = serializers.SerializerMethodField()
    active_episode = serializers.SerializerMethodField()
    medical_file = serializers.SerializerMethodField()

    class Meta(PatientListSerializer.Meta):
        fields = PatientListSerializer.Meta.fields + (
            "gender_identity",
            "blood_type",
            "phone",
            "email",
            "address",
            "emergency_contact_name",
            "emergency_contact_phone",
            "care_team",
            "active_episode",
            "medical_file",
            "updated_at",
        )

    def get_care_team(self, patient):
        assignments = getattr(patient, "active_assignments", None)
        if assignments is None:
            assignments = patient.care_assignments.filter(ends_at__isnull=True).select_related(
                "staff__user"
            )
        return CareTeamMemberSerializer(assignments, many=True).data

    def get_active_episode(self, patient):
        episodes = getattr(patient, "active_episodes", None)
        episode = (
            episodes[0]
            if episodes
            else patient.care_episodes.filter(status="ACTIVE").select_related("department").first()
        )
        return CareEpisodeSerializer(episode).data if episode else None

    def get_medical_file(self, patient):
        request = self.context.get("request")
        if request and request.user.role == UserRole.PATIENT_GUARD:
            allowed = patient.guardian_accesses.filter(
                guardian__user=request.user,
                status="ACTIVE",
                can_view_medical_file=True,
            ).exists()
            if not allowed:
                return None
        try:
            medical_file = patient.medical_file
        except Patient.medical_file.RelatedObjectDoesNotExist:
            return None
        return {
            "id": str(medical_file.id),
            "file_number": medical_file.file_number,
            "status": medical_file.status,
        }


class PatientRegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    date_of_birth = serializers.DateField()
    sex_at_birth = serializers.ChoiceField(choices=Patient.SexAtBirth.choices)
    gender_identity = serializers.CharField(max_length=80, required=False, allow_blank=True)
    blood_type = serializers.CharField(max_length=8, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    address = serializers.CharField()
    emergency_contact_name = serializers.CharField(max_length=140)
    emergency_contact_phone = serializers.CharField(max_length=32)
    assigned_nurse = serializers.PrimaryKeyRelatedField(queryset=StaffProfile.objects.all())
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True)
    )
    episode_type = serializers.ChoiceField(choices=CareEpisode.Type.choices)
    admission_reason = serializers.CharField()

    def validate_date_of_birth(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value

    def validate_assigned_nurse(self, value):
        if (
            value.user.role != UserRole.NURSE
            or not value.user.is_active
            or value.employment_status != EmploymentStatus.ACTIVE
        ):
            raise serializers.ValidationError("Select an active Nurse.")
        return value

    def patient_data(self) -> dict:
        excluded = {"assigned_nurse", "department", "episode_type", "admission_reason"}
        return {key: value for key, value in self.validated_data.items() if key not in excluded}


class PatientUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = (
            "phone",
            "email",
            "address",
            "emergency_contact_name",
            "emergency_contact_phone",
            "blood_type",
            "gender_identity",
        )


class NurseAssignmentSerializer(serializers.Serializer):
    nurse = serializers.PrimaryKeyRelatedField(queryset=StaffProfile.objects.all())

    def validate_nurse(self, value):
        if (
            value.user.role != UserRole.NURSE
            or not value.user.is_active
            or value.employment_status != EmploymentStatus.ACTIVE
        ):
            raise serializers.ValidationError("Select an active Nurse.")
        return value
