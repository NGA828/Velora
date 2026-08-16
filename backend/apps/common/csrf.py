from django.http import JsonResponse


def csrf_failure(request, reason=""):
    return JsonResponse(
        {
            "error": {
                "code": "csrf_failed",
                "message": "The security token is missing or invalid. Refresh and try again.",
                "fields": {},
                "request_id": getattr(request, "request_id", None),
            }
        },
        status=403,
    )
