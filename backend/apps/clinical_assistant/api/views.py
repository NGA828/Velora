from __future__ import annotations

import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_audit_event
from apps.clinical_assistant.api.serializers import (
    AssistantMessageSerializer,
    AssistantSessionSerializer,
    ChatRequestSerializer,
    ChatResponseSerializer,
)
from apps.clinical_assistant.models import (
    AssistantAuditLog,
    AssistantMessage,
    AssistantSession,
)
from apps.clinical_assistant.permissions import ClinicalAssistantPermission
from apps.clinical_assistant.services.context_builder import build_clinical_context
from apps.clinical_assistant.services.deepseek_service import deepseek_service
from apps.clinical_assistant.services.prompts import build_system_prompt
from apps.clinical_assistant.services.safety_validator import SafetyValidator
from apps.common.throttling import ActionScopedThrottleMixin
from apps.patients.models import Patient
from apps.patients.selectors import patients_visible_to

logger = logging.getLogger(__name__)


class ChatAPIView(ActionScopedThrottleMixin, APIView):
    permission_classes = [permissions.IsAuthenticated, ClinicalAssistantPermission]
    throttle_scope_by_action = {"post": "clinical_write"}

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        patient_id = data["patient_id"]
        user_message_text = data["message"].strip()
        session_id = data.get("session_id")

        # 1. Authorize Patient Access
        patient = get_object_or_404(Patient, pk=patient_id)
        if not ClinicalAssistantPermission.user_can_access_patient(user=request.user, patient=patient):
            raise PermissionDenied("You are not authorized to access clinical assistant for this patient.")

        # 2. Get or Create Assistant Session
        if session_id:
            session = get_object_or_404(AssistantSession, pk=session_id, user=request.user, patient=patient)
        else:
            session, _ = AssistantSession.objects.get_or_create(
                user=request.user,
                patient=patient,
                is_active=True,
                defaults={"title": f"Chat for {patient.get_full_name()}"},
            )

        # 3. Store User Message
        user_msg = AssistantMessage.objects.create(
            session=session,
            role=AssistantMessage.Role.USER,
            content=user_message_text,
        )

        # 4. Build Role-Tailored Structured Clinical Context
        clinical_context = build_clinical_context(user=request.user, patient=patient)

        # 5. Build System Prompt
        system_prompt = build_system_prompt(
            user_role=request.user.role,
            clinical_context=clinical_context,
        )

        # 6. Fetch Conversation History (last 8 messages for context continuity)
        past_messages = (
            session.messages.exclude(id=user_msg.id)
            .order_by("-created_at")[:8]
        )
        history_list = []
        for m in reversed(list(past_messages)):
            history_list.append({"role": m.role, "content": m.content})
        history_list.append({"role": "user", "content": user_message_text})

        # 7. Call DeepSeek Service with Graceful Fallback
        llm_result = deepseek_service.generate_chat_response(
            system_prompt=system_prompt,
            messages=history_list,
        )

        raw_llm_content = llm_result["content"]
        is_fallback = llm_result.get("fallback", False)

        # 8. Run Safety Validation Layer
        if not is_fallback:
            is_valid, validated_content, validation_notes = SafetyValidator.validate_response(
                response_text=raw_llm_content,
                clinical_context=clinical_context,
            )
        else:
            is_valid = True
            validated_content = raw_llm_content
            validation_notes = "FALLBACK_APPLIED"

        # 9. Store Assistant Response Message
        assistant_msg = AssistantMessage.objects.create(
            session=session,
            role=AssistantMessage.Role.ASSISTANT,
            content=validated_content,
            raw_llm_response=raw_llm_content,
            validation_passed=is_valid,
            validation_notes=validation_notes,
            context_snapshot=clinical_context,
        )

        # Touch session updated_at
        session.updated_at = timezone.now()
        session.save(update_fields=["updated_at"])

        # 10. Audit Logging
        recommendation_id = ""
        if clinical_context.get("icu_assessment"):
            recommendation_id = str(clinical_context["icu_assessment"].get("recommendation_id", ""))

        AssistantAuditLog.objects.create(
            session=session,
            user=request.user,
            patient=patient,
            action="CHAT_QUERY",
            question=user_message_text,
            response_preview=validated_content[:200],
            recommendation_id=recommendation_id,
            status="FALLBACK" if is_fallback else "VALIDATED" if is_valid else "VALIDATION_FAILED",
            metadata={
                "validation_passed": is_valid,
                "validation_notes": validation_notes,
                "role": request.user.role,
                "fallback": is_fallback,
            },
        )

        record_audit_event(
            actor=request.user,
            request=request,
            action="clinical_assistant.chat.query",
            object_type="clinical_assistant.AssistantSession",
            object_id=str(session.id),
            after={
                "patient_id": str(patient.id),
                "role": request.user.role,
                "status": "SUCCESS" if is_valid else "VALIDATION_FAILED",
                "fallback": is_fallback,
            },
        )

        # 11. Context Summary for Frontend Header
        context_summary = {
            "vital_status": clinical_context.get("latest_vitals", {}).get("status") if clinical_context.get("latest_vitals") else "UNASSESSED",
            "icu_eligible": clinical_context.get("icu_assessment", {}).get("eligible", False) if clinical_context.get("icu_assessment") else False,
            "icu_score": clinical_context.get("icu_assessment", {}).get("readiness_score", None) if clinical_context.get("icu_assessment") else None,
            "specialist_status": clinical_context.get("icu_assessment", {}).get("specialist_status", None) if clinical_context.get("icu_assessment") else None,
            "icu_bed_status": clinical_context.get("icu_assessment", {}).get("icu_bed_status", None) if clinical_context.get("icu_assessment") else None,
        }

        return Response(
            {
                "session_id": session.id,
                "message": AssistantMessageSerializer(assistant_msg).data,
                "fallback": is_fallback,
                "context_summary": context_summary,
            },
            status=status.HTTP_200_OK,
        )


class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = AssistantSessionSerializer
    permission_classes = [permissions.IsAuthenticated, ClinicalAssistantPermission]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = AssistantSession.objects.filter(user=user, is_active=True).select_related("patient").prefetch_related("messages")
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=False, methods=["get"], url_path="context")
    def patient_context(self, request):
        patient_id = request.query_params.get("patient")
        if not patient_id:
            return Response({"detail": "Patient ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        patient = get_object_or_404(Patient, pk=patient_id)
        if not ClinicalAssistantPermission.user_can_access_patient(user=request.user, patient=patient):
            raise PermissionDenied("You are not authorized to view clinical context for this patient.")

        context = build_clinical_context(user=request.user, patient=patient)
        return Response(context, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="clear")
    def clear_messages(self, request, pk=None):
        session = self.get_object()
        session.messages.all().delete()
        return Response({"status": "cleared"}, status=status.HTTP_200_OK)
