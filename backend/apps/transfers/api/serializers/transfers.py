from decimal import Decimal

from rest_framework import serializers

from apps.hospital.models import ClinicalCondition, ExternalHospital, ServiceDefinition, Specialty
from apps.identity.models import PatientGuardProfile
from apps.transfers.models import (
    TransferDecision,
    TransferRecommendation,
    TransferRequest,
    TransferRequirement,
    TransferStatusEvent,
    TransferTransmission,
)


class TransferRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransferRequirement
        fields = "__all__"


class TransferRecommendationSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source="external_hospital.name", read_only=True)
    city = serializers.CharField(source="external_hospital.city", read_only=True)
    country = serializers.CharField(source="external_hospital.country", read_only=True)
    transfer_email = serializers.EmailField(
        source="external_hospital.transfer_email", read_only=True
    )
    phone = serializers.CharField(source="external_hospital.phone", read_only=True)

    class Meta:
        model = TransferRecommendation
        fields = "__all__"


class TransferDecisionSerializer(serializers.ModelSerializer):
    guardian_name = serializers.CharField(source="guardian.user.get_full_name", read_only=True)

    class Meta:
        model = TransferDecision
        fields = "__all__"


class TransferStatusEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True)

    class Meta:
        model = TransferStatusEvent
        fields = "__all__"


class TransferTransmissionSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source="external_hospital.name", read_only=True)

    class Meta:
        model = TransferTransmission
        fields = "__all__"


class TransferRequestSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.get_full_name", read_only=True)
    medical_record_number = serializers.CharField(
        source="patient.medical_record_number", read_only=True
    )
    requested_by_name = serializers.CharField(source="requested_by.get_full_name", read_only=True)
    guardian_name = serializers.CharField(
        source="decision_guardian.user.get_full_name", read_only=True
    )
    selected_hospital_name = serializers.CharField(
        source="selected_hospital.name", read_only=True, default=None
    )
    requirements = TransferRequirementSerializer(many=True, read_only=True)
    recommendations = serializers.SerializerMethodField()
    decision = TransferDecisionSerializer(read_only=True)
    status_events = TransferStatusEventSerializer(many=True, read_only=True)
    transmissions = TransferTransmissionSerializer(many=True, read_only=True)

    class Meta:
        model = TransferRequest
        fields = "__all__"

    def get_recommendations(self, transfer):
        current = [
            item
            for item in transfer.recommendations.all()
            if item.generation == transfer.recommendation_generation
        ]
        return TransferRecommendationSerializer(current, many=True).data


class TransferRequirementInputSerializer(serializers.Serializer):
    requirement_type = serializers.ChoiceField(choices=TransferRequirement.RequirementType.choices)
    specialty = serializers.PrimaryKeyRelatedField(
        queryset=Specialty.objects.filter(is_active=True), required=False, allow_null=True
    )
    service = serializers.PrimaryKeyRelatedField(
        queryset=ServiceDefinition.objects.filter(is_active=True), required=False, allow_null=True
    )
    condition = serializers.PrimaryKeyRelatedField(
        queryset=ClinicalCondition.objects.filter(is_active=True), required=False, allow_null=True
    )
    weight = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=Decimal("0.10"),
        max_value=Decimal("100.00"),
        default=Decimal("1.00"),
    )
    is_mandatory = serializers.BooleanField(default=True)

    def validate(self, attrs):
        requirement_type = attrs["requirement_type"]
        expected = requirement_type.lower()
        selected = [key for key in ("specialty", "service", "condition") if attrs.get(key)]
        if selected != [expected]:
            raise serializers.ValidationError(
                f"Select exactly one {expected} for this requirement."
            )
        return attrs


class TransferRequestCreateSerializer(serializers.Serializer):
    patient = serializers.UUIDField()
    guardian = serializers.PrimaryKeyRelatedField(queryset=PatientGuardProfile.objects.all())
    reason = serializers.CharField()
    clinical_summary = serializers.CharField()
    urgency = serializers.ChoiceField(choices=TransferRequest.Urgency.choices)
    requirements = TransferRequirementInputSerializer(many=True, allow_empty=False)


class TransferSubmitSerializer(serializers.Serializer):
    hospital = serializers.PrimaryKeyRelatedField(
        queryset=ExternalHospital.objects.filter(is_active=True)
    )


class TransferDecisionInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=TransferDecision.Decision.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
