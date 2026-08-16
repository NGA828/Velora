import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def _message_and_fields(data, fallback: str) -> tuple[str, dict]:
    if isinstance(data, dict):
        detail = data.get("detail")
        message = str(detail) if detail else fallback
        fields = {key: value for key, value in data.items() if key != "detail"}
        return message, fields
    if isinstance(data, list):
        return fallback, {"non_field_errors": data}
    return str(data or fallback), {}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", None)

    if response is None:
        logger.exception("Unhandled API exception", extra={"request_id": request_id or "-"})
        return Response(
            {
                "error": {
                    "code": "server_error",
                    "message": "An unexpected server error occurred.",
                    "fields": {},
                    "request_id": request_id,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    fallback_messages = {
        400: "The request could not be validated.",
        401: "Authentication is required.",
        403: "You do not have permission to perform this action.",
        404: "The requested resource was not found.",
        409: "The request conflicts with the current resource state.",
        429: "Too many requests. Please try again later.",
    }
    fallback = fallback_messages.get(response.status_code, "The request could not be completed.")
    message, fields = _message_and_fields(response.data, fallback)
    code = (
        {
            400: "validation_error",
            401: "not_authenticated",
            403: "permission_denied",
            404: "not_found",
            429: "throttled",
        }.get(response.status_code)
        or getattr(exc, "default_code", None)
        or "request_error"
    )

    response.data = {
        "error": {
            "code": str(code),
            "message": message,
            "fields": fields,
            "request_id": request_id,
        }
    }
    return response
