from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import FileResponse, Http404
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_audit_event
from apps.identity.api.serializers import (
    ChangePasswordSerializer,
    InvitationAcceptSerializer,
    LoginSerializer,
    ProfileUpdateSerializer,
    SessionUserSerializer,
)
from apps.identity.models import LoginEvent, LoginOutcome, User
from apps.identity.services import accept_invitation


def _login_metadata(request) -> dict:
    return {
        "ip_address": request.META.get("REMOTE_ADDR") or None,
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:512],
    }


def _raise_drf_validation(exc: DjangoValidationError) -> None:
    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(exc.message_dict) from exc
    raise serializers.ValidationError({"detail": exc.messages}) from exc


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFCookieView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"detail": "CSRF cookie set.", "csrf_token": get_token(request)})


class SessionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": SessionUserSerializer(request.user).data})


class MeView(APIView):
    """View and update the signed-in user's own profile details (name, phone,
    profile picture). Every user can edit their own information."""

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        return Response({"user": SessionUserSerializer(request.user).data})

    @method_decorator(csrf_protect)
    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        previous = {
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "phone": request.user.phone,
            "had_avatar": bool(request.user.avatar),
        }
        serializer.save()
        record_audit_event(
            actor=request.user,
            request=request,
            action="identity.profile.updated",
            object_type="identity.User",
            object_id=request.user.id,
            after={
                "fields": sorted(serializer.validated_data.keys()),
                "avatar_changed": "avatar" in serializer.validated_data
                and bool(serializer.validated_data["avatar"]) != previous["had_avatar"],
            },
        )
        return Response({"user": SessionUserSerializer(request.user).data})


class MyAvatarView(APIView):
    """Serves the signed-in user's profile picture behind session auth."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        avatar = request.user.avatar
        if not avatar:
            raise Http404("No profile picture uploaded.")
        return FileResponse(avatar.open("rb"), content_type="image/jpeg" if not avatar.name.lower().endswith(".png") else "image/png")


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = "login"

    def get_authenticate_header(self, request):
        return "Session"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        user = authenticate(request=request, email=email, password=password)
        known_user = User.objects.filter(email__iexact=email).first()

        if user is None:
            outcome = (
                LoginOutcome.INACTIVE_ACCOUNT
                if known_user and not known_user.is_active
                else LoginOutcome.INVALID_CREDENTIALS
            )
            LoginEvent.objects.create(
                user=known_user,
                email_attempted=email,
                outcome=outcome,
                **_login_metadata(request),
            )
            raise AuthenticationFailed("The email or password is incorrect.")

        login(request, user)
        LoginEvent.objects.create(
            user=user,
            email_attempted=email,
            outcome=LoginOutcome.SUCCESS,
            **_login_metadata(request),
        )
        record_audit_event(
            actor=user,
            request=request,
            action="identity.session.started",
            object_type="identity.User",
            object_id=user.id,
        )
        return Response({"user": SessionUserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        record_audit_event(
            actor=user,
            request=request,
            action="identity.session.ended",
            object_type="identity.User",
            object_id=user.id,
        )
        LoginEvent.objects.create(
            user=user,
            email_attempted=user.email,
            outcome=LoginOutcome.LOGOUT,
            **_login_metadata(request),
        )
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        update_session_auth_hash(request, user)
        record_audit_event(
            actor=user,
            request=request,
            action="identity.password.changed",
            object_type="identity.User",
            object_id=user.id,
        )
        return Response({"user": SessionUserSerializer(user).data})


@method_decorator(csrf_protect, name="dispatch")
class InvitationAcceptView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = "invitation_accept"

    def post(self, request):
        serializer = InvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = accept_invitation(
                raw_token=data["token"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                phone=data.get("phone", ""),
                password=data["password"],
                request=request,
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        login(request, user)
        return Response({"user": SessionUserSerializer(user).data}, status=status.HTTP_201_CREATED)
