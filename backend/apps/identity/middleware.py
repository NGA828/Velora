from django.http import JsonResponse

ALLOWED_WHILE_PASSWORD_CHANGE_REQUIRED = {
    "/api/v1/auth/csrf/",
    "/api/v1/auth/session/",
    "/api/v1/auth/login/",
    "/api/v1/auth/logout/",
    "/api/v1/auth/password/change/",
}


class ForcePasswordChangeMiddleware:
    """Prevent a temporary-password account from using other API capabilities."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            request.path.startswith("/api/v1/")
            and request.path not in ALLOWED_WHILE_PASSWORD_CHANGE_REQUIRED
            and getattr(user, "is_authenticated", False)
            and user.must_change_password
        ):
            return JsonResponse(
                {
                    "error": {
                        "code": "password_change_required",
                        "message": "Change your temporary password before continuing.",
                        "fields": {},
                        "request_id": getattr(request, "request_id", None),
                    }
                },
                status=403,
            )
        return self.get_response(request)
