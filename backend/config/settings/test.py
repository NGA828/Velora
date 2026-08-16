"""Fast, deterministic test settings."""

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-only-secret-key"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
MIDDLEWARE = [  # noqa: F405
    item
    for item in MIDDLEWARE  # noqa: F405
    if item != "whitenoise.middleware.WhiteNoiseMiddleware"
]
DATABASES["default"]["NAME"] = ":memory:"  # noqa: F405
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
