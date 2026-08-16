from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.audit.models import MedicalRecordAccess
from apps.audit.services import record_medical_access
from apps.common.throttling import ActionScopedThrottleMixin
from apps.messaging.api.serializers import (
    ConversationCreateSerializer,
    ConversationSerializer,
    EligibleContactSerializer,
    MessageCreateSerializer,
    MessageSerializer,
    ReceiptAcknowledgeSerializer,
)
from apps.messaging.models import Conversation, Message, MessageAttachment
from apps.messaging.permissions import IsActiveUser
from apps.messaging.selectors import eligible_users_for
from apps.messaging.services import (
    acknowledge_messages,
    create_direct_conversation,
    send_message,
)
from apps.patients.models import Patient
from apps.patients.selectors import patients_visible_to

User = get_user_model()


def _service_error(exc):
    raise serializers.ValidationError({"detail": exc.messages}) from exc


def _conversation_queryset(user):
    return (
        Conversation.objects.filter(
            participants__user=user,
            participants__left_at__isnull=True,
        )
        .select_related("patient", "created_by")
        .prefetch_related("participants__user")
        .distinct()
    )


class ConversationViewSet(ActionScopedThrottleMixin, ReadOnlyModelViewSet):
    serializer_class = ConversationSerializer
    throttle_scope_by_action = {
        "create": "conversation_create",
        "messages": "message_send",
        "download_attachment": "attachment_download",
    }
    permission_classes = [IsActiveUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return _conversation_queryset(self.request.user)

    @action(detail=False, methods=["get"])
    def eligible(self, request):
        contacts = eligible_users_for(request.user)
        return Response(EligibleContactSerializer(contacts, many=True).data)

    def create(self, request, *args, **kwargs):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        participant = get_object_or_404(User.objects.filter(is_active=True), pk=data["participant"])
        patient = None
        if data.get("patient"):
            try:
                patient = patients_visible_to(request.user).get(pk=data["patient"])
            except Patient.DoesNotExist as exc:
                raise NotFound("Patient not found in your authorized care context.") from exc
        try:
            conversation = create_direct_conversation(
                creator=request.user,
                participant=participant,
                patient=patient,
                subject=data["subject"],
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(
            ConversationSerializer(conversation, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        conversation = self.get_object()
        if request.method == "GET":
            messages = (
                Message.objects.filter(conversation=conversation)
                .select_related("sender", "reply_to")
                .prefetch_related("receipts", "attachment")
                .order_by("-sent_at")
            )
            page = self.paginate_queryset(messages)
            serializer = MessageSerializer(
                page if page is not None else messages,
                many=True,
                context={"request": request},
            )
            if page is not None:
                return self.get_paginated_response(serializer.data)
            return Response(serializer.data)
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            message = send_message(
                conversation=conversation,
                sender=request.user,
                body=serializer.validated_data["body"],
                client_message_id=serializer.validated_data["client_message_id"],
                attachment=request.FILES.get("attachment"),
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        message = (
            Message.objects.select_related("sender")
            .prefetch_related("receipts", "attachment")
            .get(pk=message.pk)
        )
        return Response(
            MessageSerializer(message, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def _acknowledge(self, request, conversation, seen):
        serializer = ReceiptAcknowledgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            message = conversation.messages.get(pk=serializer.validated_data["up_to_message"])
        except Message.DoesNotExist as exc:
            raise NotFound("Message not found in this conversation.") from exc
        try:
            acknowledged_at = acknowledge_messages(
                conversation=conversation,
                recipient=request.user,
                up_to_message=message,
                seen=seen,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response({"acknowledged_at": acknowledged_at})

    @action(detail=True, methods=["post"])
    def delivered(self, request, pk=None):
        return self._acknowledge(request, self.get_object(), seen=False)

    @action(detail=True, methods=["post"])
    def seen(self, request, pk=None):
        return self._acknowledge(request, self.get_object(), seen=True)

    @action(
        detail=True,
        methods=["get"],
        url_path=r"attachments/(?P<attachment_id>[^/.]+)/download",
    )
    def download_attachment(self, request, pk=None, attachment_id=None):
        conversation = self.get_object()
        attachment = get_object_or_404(
            MessageAttachment.objects.select_related("message__conversation"),
            pk=attachment_id,
            message__conversation=conversation,
        )
        if conversation.patient:
            record_medical_access(
                user=request.user,
                patient=conversation.patient,
                object_type=attachment._meta.label,
                object_id=attachment.id,
                action=MedicalRecordAccess.Action.DOWNLOAD,
                purpose="Secure conversation attachment",
                request=request,
            )
        response = FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=Path(attachment.original_name).name,
            content_type=attachment.mime_type,
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'"
        return response
