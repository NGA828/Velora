"""Local development settings."""

import os

from .base import *  # noqa: F403

DEBUG = True
PREVIEW_SECURE_COOKIES = os.getenv("PREVIEW_SECURE_COOKIES", "false").lower() == "true"
SESSION_COOKIE_SECURE = PREVIEW_SECURE_COOKIES
CSRF_COOKIE_SECURE = PREVIEW_SECURE_COOKIES
if PREVIEW_SECURE_COOKIES:
    SESSION_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SAMESITE = "None"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
