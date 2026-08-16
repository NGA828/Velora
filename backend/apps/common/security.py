class SecurityHeadersMiddleware:
    """Apply conservative browser and cache controls to every Django response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault(
            "Content-Security-Policy",
            "; ".join(
                [
                    "default-src 'self'",
                    "base-uri 'self'",
                    "frame-ancestors 'none'",
                    "form-action 'self'",
                    "object-src 'none'",
                    "img-src 'self' data: blob:",
                    "style-src 'self' 'unsafe-inline'",
                    "script-src 'self'",
                    "connect-src 'self' ws: wss: https://*.twilio.com wss://*.twilio.com",
                    "media-src 'self' blob:",
                    "worker-src 'self' blob:",
                ]
            ),
        )
        response.setdefault(
            "Permissions-Policy",
            "camera=(), geolocation=(), microphone=(self), payment=(), usb=()",
        )
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if request.path.startswith("/api/v1/"):
            response["Cache-Control"] = "no-store, private"
            response["Pragma"] = "no-cache"
        return response
