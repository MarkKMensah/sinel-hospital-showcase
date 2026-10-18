"""Isolated fictional-data tests: never import workstation/live settings."""

import tempfile

from .base import *  # noqa: F403
from .ckeditor_settings import *  # noqa: F403

SECRET_KEY = "test-only-sinel-key-not-for-hosting"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
_test_media = tempfile.TemporaryDirectory(prefix="sinel-test-media-")
MEDIA_ROOT = _test_media.name

# CI may explicitly select its ephemeral PostgreSQL service. Local defaults
# remain in-memory SQLite, never the developer's working editorial database.
if os.environ.get("SINEL_TEST_POSTGRES") != "1":  # noqa: F405
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
