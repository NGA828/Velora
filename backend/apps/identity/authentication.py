from rest_framework.authentication import SessionAuthentication


class VeloraSessionAuthentication(SessionAuthentication):
    """Session authentication with an explicit challenge for consistent 401 responses."""

    def authenticate_header(self, request) -> str:
        return "Session"
