from rest_framework import serializers

from apps.identity.models import PatientGuardProfile
from apps.monitoring.models import MonitoringQuestion, MonitoringResponse, MonitoringThread


class MonitoringResponseSerializer(serializers.ModelSerializer):
    guardian_name = serializers.CharField(source="guardian.user.get_full_name", read_only=True)

    class Meta:
        model = MonitoringResponse
        fields = (
            "id",
            "guardian_name",
            "answer",
            "submitted_at",
            "is_current",
            "supersedes",
        )


class MonitoringQuestionSerializer(serializers.ModelSerializer):
    response_type_label = serializers.CharField(source="get_response_type_display", read_only=True)
    responses = MonitoringResponseSerializer(many=True, read_only=True)
    current_response = serializers.SerializerMethodField()

    class Meta:
        model = MonitoringQuestion
        fields = "__all__"

    def get_current_response(self, question):
        response = next((item for item in question.responses.all() if item.is_current), None)
        return MonitoringResponseSerializer(response).data if response else None


class MonitoringThreadSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.get_full_name", read_only=True)
    medical_record_number = serializers.CharField(
        source="patient.medical_record_number", read_only=True
    )
    doctor_name = serializers.CharField(source="doctor.get_full_name", read_only=True)
    guardian_name = serializers.CharField(source="guardian.user.get_full_name", read_only=True)
    questions = MonitoringQuestionSerializer(many=True, read_only=True)
    pending_question_count = serializers.SerializerMethodField()

    class Meta:
        model = MonitoringThread
        fields = "__all__"

    def get_pending_question_count(self, thread):
        return sum(
            1
            for question in thread.questions.all()
            if not any(response.is_current for response in question.responses.all())
        )


class MonitoringThreadCreateSerializer(serializers.Serializer):
    patient = serializers.UUIDField()
    guardian = serializers.PrimaryKeyRelatedField(queryset=PatientGuardProfile.objects.all())
    subject = serializers.CharField(max_length=180)


class MonitoringQuestionCreateSerializer(serializers.Serializer):
    prompt = serializers.CharField()
    response_type = serializers.ChoiceField(choices=MonitoringQuestion.ResponseType.choices)
    options = serializers.ListField(
        child=serializers.CharField(max_length=120), required=False, default=list
    )
    due_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        if (
            attrs["response_type"] == MonitoringQuestion.ResponseType.SINGLE_CHOICE
            and len(attrs["options"]) < 2
        ):
            raise serializers.ValidationError({"options": "Add at least two choices."})
        return attrs


class MonitoringAnswerSerializer(serializers.Serializer):
    answer = serializers.JSONField()
