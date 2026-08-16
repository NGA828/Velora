from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.calls.api.serializers import CallCreateSerializer, CallSessionSerializer
from apps.calls.models import CallSession
from apps.calls.permissions import IsActiveUser
from apps.calls.services import cancel_call, initiate_call
from apps.common.throttling import ActionScopedThrottleMixin
from apps.messaging.models import Conversation
from integrations.twilio.config import get_twilio_settings
from integrations.twilio.tokens import create_voice_token, twilio_identity

User = get_user_model()


def unavailable_response():
    return Response(
        {
            "error": {
                "code": "integration_unavailable",
                "message": "Voice calling is unavailable because Twilio is not configured.",
                "fields": {},
                "request_id": None,
            }
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


class CallSessionViewSet(ActionScopedThrottleMixin, ReadOnlyModelViewSet):
    serializer_class = CallSessionSerializer
    throttle_scope_by_action = {"create": "call_initiate", "token": "call_initiate"}
    permission_classes = [IsActiveUser]

    def get_queryset(self):
        return (
            CallSession.objects.filter(participants__user=self.request.user)
            .select_related("initiated_by", "patient", "conversation")
            .prefetch_related("participants__user")
            .distinct()
        )

    @action(detail=False, methods=["get"])
    def availability(self, request):
        return Response({"available": get_twilio_settings().available})

    @action(detail=False, methods=["get"])
    def token(self, request):
        if not get_twilio_settings().available:
            return unavailable_response()
        return Response(
            {
                "token": create_voice_token(user_id=request.user.id),
                "identity": twilio_identity(request.user.id),
                "expires_in": 3600,
            }
        )

    def create(self, request, *args, **kwargs):
        if not get_twilio_settings().available:
            return unavailable_response()
        serializer = CallCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipient = get_object_or_404(
            User.objects.filter(is_active=True), pk=serializer.validated_data["recipient"]
        )
        conversation = None
        if serializer.validated_data.get("conversation"):
            conversation = get_object_or_404(
                Conversation.objects.filter(
                    participants__user=request.user,
                    participants__left_at__isnull=True,
                ),
                pk=serializer.validated_data["conversation"],
            )
        try:
            session = initiate_call(
                caller=request.user,
                recipient=recipient,
                conversation=conversation,
                request=request,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"detail": exc.messages}) from exc
        return Response(
            CallSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        try:
            session = cancel_call(session=self.get_object(), actor=request.user, request=request)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"detail": exc.messages}) from exc
        return Response(CallSessionSerializer(session).data)
