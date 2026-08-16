from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.identity.models import UserRole
from apps.monitoring.api.serializers import (
    MonitoringAnswerSerializer,
    MonitoringQuestionCreateSerializer,
    MonitoringThreadCreateSerializer,
    MonitoringThreadSerializer,
)
from apps.monitoring.models import MonitoringQuestion, MonitoringResponse, MonitoringThread
from apps.monitoring.permissions import MonitoringPermission
from apps.monitoring.services import add_question, answer_question, close_thread, create_thread
from apps.patients.models import Patient
from apps.patients.selectors import patients_visible_to


def _service_error(exc):
    raise serializers.ValidationError({"detail": exc.messages}) from exc


class MonitoringThreadViewSet(ReadOnlyModelViewSet):
    permission_classes = [MonitoringPermission]

    def get_serializer_class(self):
        return (
            MonitoringThreadCreateSerializer
            if self.action == "create"
            else MonitoringThreadSerializer
        )

    def get_queryset(self):
        responses = MonitoringResponse.objects.select_related("guardian__user")
        questions = MonitoringQuestion.objects.prefetch_related(
            Prefetch("responses", queryset=responses)
        )
        queryset = MonitoringThread.objects.select_related(
            "patient", "doctor", "guardian__user"
        ).prefetch_related(Prefetch("questions", queryset=questions))
        if self.request.user.role == UserRole.DOCTOR:
            queryset = queryset.filter(
                doctor=self.request.user,
                patient__in=patients_visible_to(self.request.user),
            )
        else:
            queryset = queryset.filter(guardian__user=self.request.user)
        patient = self.request.query_params.get("patient")
        return queryset.filter(patient_id=patient) if patient else queryset

    def create(self, request, *args, **kwargs):
        serializer = MonitoringThreadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            patient = patients_visible_to(request.user).get(pk=serializer.validated_data["patient"])
        except Patient.DoesNotExist as exc:
            raise NotFound("Patient not found in your assigned care list.") from exc
        try:
            thread = create_thread(
                patient=patient,
                doctor=request.user,
                guardian=serializer.validated_data["guardian"],
                subject=serializer.validated_data["subject"],
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(
            MonitoringThreadSerializer(self.get_queryset().get(pk=thread.pk)).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="questions")
    def add_question(self, request, pk=None):
        serializer = MonitoringQuestionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            add_question(
                thread=self.get_object(),
                doctor=request.user,
                request=request,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(MonitoringThreadSerializer(self.get_queryset().get(pk=pk)).data)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"questions/(?P<question_id>[^/.]+)/answer",
    )
    def answer(self, request, pk=None, question_id=None):
        thread = self.get_object()
        try:
            question = thread.questions.get(pk=question_id)
        except MonitoringQuestion.DoesNotExist as exc:
            raise NotFound("Monitoring question not found.") from exc
        serializer = MonitoringAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            answer_question(
                question=question,
                guardian=request.user.patient_guard_profile,
                answer=serializer.validated_data["answer"],
                request=request,
            )
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(MonitoringThreadSerializer(self.get_queryset().get(pk=pk)).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        try:
            thread = close_thread(thread=self.get_object(), doctor=request.user, request=request)
        except DjangoValidationError as exc:
            _service_error(exc)
        return Response(MonitoringThreadSerializer(thread).data)
